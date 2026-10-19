import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import ProtectedError
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import User
from properties.models import House, HouseImage, Location


def make_house(landlord, location, title, rent, beds=1, baths=1, typ="apartment", status="vacant"):
    return House.objects.create(
        landlord=landlord, location=location, title=title, rent=rent,
        bedrooms=beds, bathrooms=baths, house_type=typ, status=status,
    )


class LandingAndSearch(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ll = User.objects.create_user("land", "l@x.com", "pw-12345-abc", role="landlord", phone_number="0700")
        cls.town = Location.objects.create(name="Murang'a Town")
        cls.mjini = Location.objects.create(name="Mjini")
        make_house(cls.ll, cls.town, "Cheap bedsitter", 3500, 1, 1, "bedsitter")
        make_house(cls.ll, cls.town, "Mid apartment", 8000, 2, 1, "apartment")
        make_house(cls.ll, cls.mjini, "Pricey maisonette", 25000, 3, 3, "maisonette")
        make_house(cls.ll, cls.town, "Taken flat", 9000, 2, 1, "apartment", status="occupied")

    def titles(self, **params):
        r = self.client.get(reverse("properties:house_list"), params)
        self.assertEqual(r.status_code, 200)
        return sorted(h.title for h in r.context["page_obj"])

    def test_landing_renders_all_sections_in_order(self):
        r = self.client.get(reverse("properties:home"))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        for needle in ["Find Your Dream Home", "Live Your Best Life", "Explore Properties", "How It Works",
                       "Search Properties", "What Our Clients Say", "Follow us:", "Find. Buy. Live Better.",
                       "Property Types", "Contact Us", "for your dream home", 'id="how-it-works"', "Cheap bedsitter"]:
            self.assertIn(needle, html, needle)
        self.assertEqual(html.count("fa-quote-left"), 3)
        self.assertNotIn("Taken flat", html)
        self.assertLess(html.index('<div class="topbar">'), html.index('<nav class="site-nav"'))
        self.assertLess(html.index('<nav class="site-nav"'), html.index('<section class="hx">'))
        self.assertLess(html.index('<section class="hx">'), html.index("<main>"))

    def test_landing_with_no_houses_shows_sample_card(self):
        House.objects.all().delete()
        self.assertContains(self.client.get(reverse("properties:home")), "Modern Family Home")

    def test_only_vacant_houses_are_searchable(self):
        self.assertEqual(len(self.titles()), 3)
        self.assertNotIn("Taken flat", self.titles())

    def test_price_range_filter(self):
        self.assertEqual(self.titles(price_range="0-5000"), ["Cheap bedsitter"])
        self.assertEqual(self.titles(price_range="5000-10000"), ["Mid apartment"])
        self.assertEqual(self.titles(price_range="20000-"), ["Pricey maisonette"])

    def test_price_range_fills_the_rent_fields_on_the_results_page(self):
        r = self.client.get(reverse("properties:house_list"), {"price_range": "5000-10000"})
        self.assertContains(r, 'value="5000"')
        self.assertContains(r, 'value="10000"')

    def test_type_bathrooms_bedrooms_and_location_filters(self):
        self.assertEqual(self.titles(house_type="apartment"), ["Mid apartment"])
        self.assertEqual(self.titles(bathrooms="2"), ["Pricey maisonette"])      # at least 2
        self.assertEqual(self.titles(bedrooms="2"), ["Mid apartment"])           # exactly 2
        self.assertEqual(self.titles(location=self.mjini.pk), ["Pricey maisonette"])

    def test_combined_filters(self):
        self.assertEqual(self.titles(location=self.town.pk, house_type="apartment", price_range="5000-10000",
                                     bedrooms="2", bathrooms="1"), ["Mid apartment"])

    def test_explicit_rent_beats_price_range(self):
        self.assertEqual(self.titles(price_range="0-5000", min_rent="7000", max_rent="9000"), ["Mid apartment"])

    def test_min_rent_above_max_rent_is_rejected_gracefully(self):
        r = self.client.get(reverse("properties:house_list"), {"min_rent": "9000", "max_rent": "1000"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Min rent cannot be higher than max rent")

    def test_results_are_paged_twelve_at_a_time(self):
        for i in range(14):
            make_house(self.ll, self.town, f"Extra {i}", 6000)
        first = self.client.get(reverse("properties:house_list")).context["page_obj"]
        second = self.client.get(reverse("properties:house_list"), {"page": 2}).context["page_obj"]
        self.assertEqual((len(first), first.paginator.count), (12, 17))
        self.assertEqual(len(second), 5)

    def test_footer_and_top_bar_appear_on_other_pages(self):
        page = self.client.get(reverse("properties:house_list"))
        self.assertContains(page, "Quick Links")
        self.assertContains(page, "Follow us:")


class LandlordListings(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.town = Location.objects.create(name="Murang'a Town")
        cls.landlord = User.objects.create_user("owner", "o@x.com", "pw-12345-abc", role="landlord", phone_number="+254700000001")
        cls.other = User.objects.create_user("other", "x@x.com", "pw-12345-abc", role="landlord", phone_number="+254700000002")
        cls.tenant = User.objects.create_user("tenant", "t@x.com", "pw-12345-abc", role="tenant")
        cls.house = make_house(cls.landlord, cls.town, "Owner's house", 9000)
        cls.other_house = make_house(cls.other, cls.town, "Other's house", 7000)

    def form_data(self, **extra):
        data = {"title": "New 2 bedroom", "location": self.town.pk, "rent": 11000, "bedrooms": 2,
                "bathrooms": 1, "house_type": "apartment", "status": "vacant", "description": "Near the market"}
        data.update(extra)
        return data

    def test_landlord_pages_need_login(self):
        for name in ["properties:my_houses", "properties:house_create"]:
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302, name)
            self.assertIn("/accounts/login/", r["Location"])

    def test_tenants_are_refused_landlord_pages(self):
        self.client.force_login(self.tenant)
        for name in ["properties:my_houses", "properties:house_create"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_landlord_creates_a_house_they_own(self):
        self.client.force_login(self.landlord)
        r = self.client.post(reverse("properties:house_create"), self.form_data())
        created = House.objects.get(title="New 2 bedroom")
        self.assertRedirects(r, reverse("properties:image_upload", args=[created.pk]))
        self.assertEqual((created.landlord, created.rent, created.status), (self.landlord, 11000, "vacant"))

    def test_invalid_house_is_not_saved(self):
        self.client.force_login(self.landlord)
        for bad in ({"rent": 0}, {"rent": "abc"}, {"title": ""}, {"location": 9999}, {"house_type": "castle"}):
            self.client.post(reverse("properties:house_create"), self.form_data(**bad))
        self.assertEqual(House.objects.count(), 2)

    def test_my_houses_lists_only_own_houses(self):
        self.client.force_login(self.landlord)
        page = self.client.get(reverse("properties:my_houses"))
        self.assertContains(page, "Owner&#x27;s house")
        self.assertNotContains(page, "Other&#x27;s house")

    def test_landlord_cannot_touch_another_landlords_house(self):
        self.client.force_login(self.landlord)
        pk = self.other_house.pk
        self.assertEqual(self.client.get(reverse("properties:house_update", args=[pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("properties:house_update", args=[pk]), self.form_data()).status_code, 404)
        self.assertEqual(self.client.post(reverse("properties:house_delete", args=[pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("properties:toggle_status", args=[pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("properties:image_upload", args=[pk])).status_code, 404)
        self.other_house.refresh_from_db()
        self.assertEqual((self.other_house.title, self.other_house.status), ("Other's house", "vacant"))

    def test_edit_updates_the_house(self):
        self.client.force_login(self.landlord)
        self.client.post(reverse("properties:house_update", args=[self.house.pk]), self.form_data(title="Renamed", rent=9500))
        self.house.refresh_from_db()
        self.assertEqual((self.house.title, self.house.rent), ("Renamed", 9500))

    def test_delete_and_toggle_need_post(self):
        self.client.force_login(self.landlord)
        self.assertEqual(self.client.get(reverse("properties:house_delete", args=[self.house.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("properties:toggle_status", args=[self.house.pk])).status_code, 405)
        self.assertTrue(House.objects.filter(pk=self.house.pk).exists())

    def test_toggle_switches_between_vacant_and_occupied(self):
        self.client.force_login(self.landlord)
        url = reverse("properties:toggle_status", args=[self.house.pk])
        self.client.post(url)
        self.house.refresh_from_db()
        self.assertEqual(self.house.status, "occupied")
        self.client.post(url)
        self.house.refresh_from_db()
        self.assertEqual(self.house.status, "vacant")

    def test_delete_removes_the_house(self):
        self.client.force_login(self.landlord)
        self.client.post(reverse("properties:house_delete", args=[self.house.pk]))
        self.assertFalse(House.objects.filter(pk=self.house.pk).exists())

    def test_location_in_use_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.town.delete()

    def test_photo_upload_and_delete(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        with override_settings(MEDIA_ROOT=tmp):
            buffer = BytesIO()
            Image.new("RGB", (20, 20), "green").save(buffer, "PNG")
            self.client.force_login(self.landlord)
            r = self.client.post(
                reverse("properties:image_upload", args=[self.house.pk]),
                {"image": SimpleUploadedFile("photo.png", buffer.getvalue(), content_type="image/png")},
            )
            self.assertRedirects(r, reverse("properties:image_upload", args=[self.house.pk]))
            image = HouseImage.objects.get()
            self.assertEqual(image.house, self.house)
            # another landlord cannot delete it
            self.client.force_login(self.other)
            self.assertEqual(self.client.post(reverse("properties:image_delete", args=[image.pk])).status_code, 404)
            self.client.force_login(self.landlord)
            self.client.post(reverse("properties:image_delete", args=[image.pk]))
            self.assertEqual(HouseImage.objects.count(), 0)

    def test_non_image_upload_is_rejected(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        with override_settings(MEDIA_ROOT=tmp):
            self.client.force_login(self.landlord)
            self.client.post(
                reverse("properties:image_upload", args=[self.house.pk]),
                {"image": SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")},
            )
            self.assertEqual(HouseImage.objects.count(), 0)