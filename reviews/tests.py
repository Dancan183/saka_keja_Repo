import re

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from inquiries.models import Inquiry
from properties.models import House, Location
from reviews import services
from reviews.models import Review, ReviewReport
from reviews.templatetags.review_extras import stars

User = get_user_model()


class ReviewTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.town = Location.objects.create(name="Murang'a Town")
        cls.landlord = User.objects.create_user("landlord1", "l1@x.com", "pw-12345-abc", role="landlord", phone_number="+254700000001")
        cls.landlord2 = User.objects.create_user("landlord2", "l2@x.com", "pw-12345-abc", role="landlord", phone_number="+254700000002")
        cls.tenant = User.objects.create_user("tenant1", "t1@x.com", "pw-12345-abc", role="tenant")
        cls.tenant2 = User.objects.create_user("tenant2", "t2@x.com", "pw-12345-abc", role="tenant")
        cls.stranger = User.objects.create_user("stranger", "s@x.com", "pw-12345-abc", role="tenant")
        cls.house = House.objects.create(landlord=cls.landlord, location=cls.town, title="Two bedroom in Mukuyu", rent=12000)
        cls.house2 = House.objects.create(landlord=cls.landlord2, location=cls.town, title="Bedsitter in Mjini", rent=5000)
        # tenant1 asked landlord1; tenant2 asked landlord1; nobody asked landlord2
        Inquiry.objects.create(house=cls.house, tenant=cls.tenant, message="Is it available?")
        Inquiry.objects.create(house=cls.house, tenant=cls.tenant2, message="Can I view it?")

    def review(self, reviewer, reviewee, rating=4, comment="Good", **kw):
        return Review.objects.create(reviewer=reviewer, reviewee=reviewee, rating=rating, comment=comment, **kw)

    def post_review(self, user, reviewee, **data):
        self.client.force_login(user)
        return self.client.post(reverse("reviews:write_review", args=[reviewee.pk]), data)


class Eligibility(ReviewTestBase):
    def test_tenant_who_inquired_can_review_the_landlord(self):
        self.assertTrue(services.can_review(self.tenant, self.landlord))

    def test_landlord_can_review_a_tenant_who_inquired(self):
        self.assertTrue(services.can_review(self.landlord, self.tenant))

    def test_no_review_without_an_inquiry(self):
        self.assertFalse(services.can_review(self.stranger, self.landlord))
        self.assertFalse(services.can_review(self.tenant, self.landlord2))   # asked a different landlord
        self.assertFalse(services.can_review(self.landlord2, self.tenant))   # inquiry went to landlord1, not landlord2

    def test_same_role_and_self_not_allowed(self):
        self.assertFalse(services.can_review(self.tenant, self.tenant2))
        self.assertFalse(services.can_review(self.landlord, self.landlord2))
        self.assertFalse(services.can_review(self.tenant, self.tenant))

    def test_anonymous_cannot_review(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(services.can_review(AnonymousUser(), self.landlord))

    def test_write_page_requires_login(self):
        r = self.client.get(reverse("reviews:write_review", args=[self.landlord.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])

    def test_ineligible_user_is_refused_and_nothing_is_saved(self):
        r = self.post_review(self.stranger, self.landlord, rating=5, comment="Never met them")
        self.assertRedirects(r, reverse("properties:home"), fetch_redirect_response=False)
        self.assertEqual(Review.objects.count(), 0)


class WritingReviews(ReviewTestBase):
    def test_tenant_posts_a_review_and_it_shows_on_the_landlord_profile(self):
        r = self.post_review(self.tenant, self.landlord, rating=5, comment="Fair rent and quick replies")
        self.assertRedirects(r, reverse("reviews:landlord_profile", args=[self.landlord.pk]), fetch_redirect_response=False)
        review = Review.objects.get()
        self.assertEqual((review.reviewer, review.reviewee, review.rating), (self.tenant, self.landlord, 5))
        self.assertEqual(review.house, self.house)                    # context taken from the inquiry
        page = self.client.get(reverse("reviews:landlord_profile", args=[self.landlord.pk]))
        self.assertContains(page, "Fair rent and quick replies")
        self.assertContains(page, "tenant1")

    def test_second_submission_edits_instead_of_duplicating(self):
        self.post_review(self.tenant, self.landlord, rating=2, comment="Slow")
        self.post_review(self.tenant, self.landlord, rating=4, comment="Improved")
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual((Review.objects.get().rating, Review.objects.get().comment), (4, "Improved"))

    def test_edit_page_is_prefilled(self):
        self.review(self.tenant, self.landlord, rating=3, comment="Okay")
        self.client.force_login(self.tenant)
        r = self.client.get(reverse("reviews:write_review", args=[self.landlord.pk]))
        self.assertContains(r, "Edit your review")
        self.assertContains(r, "Okay")
        self.assertRegex(r.content.decode(), r'value="3"[^>]*checked|checked[^>]*value="3"')

    def test_star_picker_renders_five_styled_radio_buttons(self):
        self.client.force_login(self.tenant)
        html = self.client.get(reverse("reviews:write_review", args=[self.landlord.pk])).content.decode()
        inputs = re.findall(r'<input[^>]*type="radio"[^>]*>', html)
        self.assertEqual(len(inputs), 5)
        self.assertTrue(all('class="star-radio"' in i for i in inputs))
        self.assertEqual([re.search(r'value="(\d)"', i).group(1) for i in inputs], ["5", "4", "3", "2", "1"])

    def test_rating_is_validated(self):
        for bad in ["", "0", "6", "-1", "abc", "4.5"]:
            self.post_review(self.tenant, self.landlord, rating=bad, comment="x")
            self.assertEqual(Review.objects.count(), 0, bad)

    def test_comment_is_optional_and_limited_to_500_characters(self):
        self.post_review(self.tenant, self.landlord, rating=4)
        self.assertEqual(Review.objects.get().comment, "")
        Review.objects.all().delete()
        self.post_review(self.tenant, self.landlord, rating=4, comment="x" * 501)
        self.assertEqual(Review.objects.count(), 0)
        self.post_review(self.tenant, self.landlord, rating=4, comment="x" * 500)
        self.assertEqual(Review.objects.count(), 1)

    def test_html_in_comments_is_escaped(self):
        self.post_review(self.tenant, self.landlord, rating=3, comment="<script>alert(1)</script> <b>bold</b>")
        page = self.client.get(reverse("reviews:landlord_profile", args=[self.landlord.pk])).content.decode()
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)

    def test_landlord_reviews_a_tenant(self):
        r = self.post_review(self.landlord, self.tenant, rating=5, comment="Paid on time")
        self.assertRedirects(r, reverse("reviews:tenant_profile", args=[self.tenant.pk]), fetch_redirect_response=False)
        self.assertEqual(Review.objects.get().reviewee, self.tenant)

    def test_database_enforces_the_rules_too(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.create(reviewer=self.tenant, reviewee=self.landlord, rating=6)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.create(reviewer=self.tenant, reviewee=self.landlord, rating=0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.create(reviewer=self.tenant, reviewee=self.tenant, rating=3)
        self.review(self.tenant, self.landlord)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.review(self.tenant, self.landlord)

    def test_deleting_the_house_keeps_the_review(self):
        self.review(self.tenant, self.landlord, house=self.house)
        self.house.delete()
        self.assertIsNone(Review.objects.get().house)


class Profiles(ReviewTestBase):
    def test_landlord_profile_is_public_and_shows_stats(self):
        self.review(self.tenant, self.landlord, rating=5, comment="Great")
        self.review(self.tenant2, self.landlord, rating=4, comment="Good")
        r = self.client.get(reverse("reviews:landlord_profile", args=[self.landlord.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["stats"]["average"], 4.5)
        self.assertEqual(r.context["stats"]["count"], 2)
        self.assertEqual([row["count"] for row in r.context["stats"]["breakdown"]], [1, 1, 0, 0, 0])
        self.assertContains(r, "Two bedroom in Mukuyu")               # the landlord's listings
        self.assertContains(r, "Log in</a> to leave a review")        # anonymous visitors

    def test_hidden_reviews_are_excluded_from_page_and_numbers(self):
        self.review(self.tenant, self.landlord, rating=5, comment="Visible one")
        self.review(self.tenant2, self.landlord, rating=1, comment="Hidden one", is_visible=False)
        r = self.client.get(reverse("reviews:landlord_profile", args=[self.landlord.pk]))
        self.assertContains(r, "Visible one")
        self.assertNotContains(r, "Hidden one")
        self.assertEqual((r.context["stats"]["average"], r.context["stats"]["count"]), (5.0, 1))

    def test_landlord_with_no_reviews(self):
        r = self.client.get(reverse("reviews:landlord_profile", args=[self.landlord2.pk]))
        self.assertContains(r, "No reviews yet")
        self.assertIsNone(r.context["stats"]["average"])

    def test_profile_of_a_non_landlord_is_404(self):
        self.assertEqual(self.client.get(reverse("reviews:landlord_profile", args=[self.tenant.pk])).status_code, 404)

    def test_write_button_only_for_eligible_tenants(self):
        url = reverse("reviews:landlord_profile", args=[self.landlord.pk])
        self.client.force_login(self.tenant)
        self.assertContains(self.client.get(url), "Write a review")
        self.client.force_login(self.stranger)
        page = self.client.get(url)
        self.assertNotContains(page, "Write a review")
        self.assertContains(page, "Only tenants who sent this landlord an inquiry")

    def test_tenant_reviews_are_private(self):
        self.review(self.landlord, self.tenant, rating=2, comment="Late payer")
        url = reverse("reviews:tenant_profile", args=[self.tenant.pk])
        # anonymous: sent to login
        self.assertIn("/accounts/login/", self.client.get(url)["Location"])
        # another tenant, a landlord the tenant never contacted: refused
        for outsider in (self.stranger, self.tenant2, self.landlord2):
            self.client.force_login(outsider)
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, outsider.username)
            self.assertNotIn("Late payer", self.client.get(url, follow=True).content.decode())
        # the tenant, the landlord they contacted, and staff: allowed
        staff = User.objects.create_user("staff", "st@x.com", "pw-12345-abc", is_staff=True)
        for insider in (self.tenant, self.landlord, staff):
            self.client.force_login(insider)
            self.assertContains(self.client.get(url), "Late payer")

    def test_landlord_written_reviews_never_count_towards_the_landlord_rating(self):
        self.review(self.landlord, self.tenant, rating=1, comment="x")
        self.assertEqual(services.rating_stats(services.reviews_about_landlord(self.landlord))["count"], 0)

    def test_pagination(self):
        for i in range(12):
            t = User.objects.create_user(f"tt{i}", f"tt{i}@x.com", "pw-12345-abc")
            Inquiry.objects.create(house=self.house, tenant=t, message="hi")
            self.review(t, self.landlord, rating=3, comment=f"review number {i}")
        url = reverse("reviews:landlord_profile", args=[self.landlord.pk])
        self.assertEqual(len(self.client.get(url).context["page_obj"]), 10)
        self.assertEqual(len(self.client.get(url + "?page=2").context["page_obj"]), 2)


class DeletingAndReporting(ReviewTestBase):
    def test_author_can_delete_only_with_post(self):
        review = self.review(self.tenant, self.landlord)
        self.client.force_login(self.tenant)
        self.assertEqual(self.client.get(reverse("reviews:delete_review", args=[review.pk])).status_code, 405)
        self.assertEqual(Review.objects.count(), 1)
        self.client.post(reverse("reviews:delete_review", args=[review.pk]))
        self.assertEqual(Review.objects.count(), 0)

    def test_others_cannot_delete_a_review(self):
        review = self.review(self.tenant, self.landlord)
        for other in (self.tenant2, self.landlord):
            self.client.force_login(other)
            self.assertEqual(self.client.post(reverse("reviews:delete_review", args=[review.pk])).status_code, 404)
        self.assertEqual(Review.objects.count(), 1)

    def test_report_a_public_review(self):
        review = self.review(self.tenant, self.landlord, comment="Not true")
        self.client.force_login(self.landlord)
        self.client.post(reverse("reviews:report_review", args=[review.pk]), {"reason": "fake", "note": "Never rented"})
        report = ReviewReport.objects.get()
        self.assertEqual((report.reporter, report.reason, report.note), (self.landlord, "fake", "Never rented"))
        review.refresh_from_db()
        self.assertTrue(review.is_visible)                            # a report alone never hides a review

    def test_duplicate_report_is_ignored_and_reason_is_required(self):
        review = self.review(self.tenant, self.landlord)
        self.client.force_login(self.landlord)
        url = reverse("reviews:report_review", args=[review.pk])
        self.client.post(url, {"reason": "abusive"})
        self.client.post(url, {"reason": "fake"})
        self.assertEqual(ReviewReport.objects.count(), 1)
        self.client.post(reverse("reviews:report_review", args=[self.review(self.tenant2, self.landlord).pk]), {"reason": "nonsense"})
        self.assertEqual(ReviewReport.objects.count(), 1)

    def test_cannot_report_your_own_review_or_use_get(self):
        review = self.review(self.tenant, self.landlord)
        self.client.force_login(self.tenant)
        self.client.post(reverse("reviews:report_review", args=[review.pk]), {"reason": "fake"})
        self.assertEqual(ReviewReport.objects.count(), 0)
        self.assertEqual(self.client.get(reverse("reviews:report_review", args=[review.pk])).status_code, 405)

    def test_reports_need_login(self):
        review = self.review(self.tenant, self.landlord)
        r = self.client.post(reverse("reviews:report_review", args=[review.pk]), {"reason": "fake"})
        self.assertIn("/accounts/login/", r["Location"])

    def test_private_reviews_can_be_reported_only_by_the_tenant_they_are_about(self):
        review = self.review(self.landlord, self.tenant, rating=1, comment="Unfair")
        url = reverse("reviews:report_review", args=[review.pk])
        for outsider in (self.tenant2, self.stranger, self.landlord2):
            self.client.force_login(outsider)
            self.client.post(url, {"reason": "fake"})
        self.assertEqual(ReviewReport.objects.count(), 0)
        self.client.force_login(self.tenant)
        self.client.post(url, {"reason": "fake"})
        self.assertEqual(ReviewReport.objects.count(), 1)

    def test_reporting_a_hidden_review_is_404(self):
        review = self.review(self.tenant, self.landlord, is_visible=False)
        self.client.force_login(self.landlord)
        self.assertEqual(self.client.post(reverse("reviews:report_review", args=[review.pk]), {"reason": "fake"}).status_code, 404)


class MyReviewsAndIntegration(ReviewTestBase):
    def test_my_reviews_lists_people_still_to_review_then_drops_them(self):
        self.client.force_login(self.tenant)
        page = self.client.get(reverse("reviews:my_reviews"))
        self.assertEqual([p.pk for p in page.context["to_review"]], [self.landlord.pk])
        self.review(self.tenant, self.landlord, comment="Done now")
        page = self.client.get(reverse("reviews:my_reviews"))
        self.assertEqual(len(page.context["to_review"]), 0)
        self.assertContains(page, "Done now")

    def test_landlord_sees_tenants_waiting_for_a_review_and_reviews_about_them(self):
        self.review(self.tenant, self.landlord, rating=5, comment="Lovely landlord")
        self.client.force_login(self.landlord)
        page = self.client.get(reverse("reviews:my_reviews"))
        self.assertEqual({p.pk for p in page.context["to_review"]}, {self.tenant.pk, self.tenant2.pk})
        self.assertContains(page, "Lovely landlord")

    def test_author_still_sees_a_review_hidden_by_moderators(self):
        self.review(self.tenant, self.landlord, comment="My hidden words", is_visible=False)
        self.client.force_login(self.tenant)
        self.assertContains(self.client.get(reverse("reviews:my_reviews")), "Hidden by the moderators")

    def test_house_page_shows_the_landlord_rating(self):
        self.review(self.tenant, self.landlord, rating=4)
        page = self.client.get(reverse("properties:house_detail", args=[self.house.pk]))
        self.assertContains(page, "1 review")
        self.assertContains(page, reverse("reviews:landlord_profile", args=[self.landlord.pk]))
        empty = self.client.get(reverse("properties:house_detail", args=[self.house2.pk]))
        self.assertContains(empty, "No reviews yet")

    def test_inquiry_pages_link_to_reviews(self):
        self.client.force_login(self.tenant)
        sent = self.client.get(reverse("inquiries:sent"))
        self.assertContains(sent, reverse("reviews:write_review", args=[self.landlord.pk]))
        self.client.force_login(self.landlord)
        inbox = self.client.get(reverse("inquiries:inbox"))
        self.assertContains(inbox, reverse("reviews:tenant_profile", args=[self.tenant.pk]))
        self.assertContains(inbox, reverse("reviews:write_review", args=[self.tenant.pk]))

    def test_navigation_has_a_reviews_link_when_logged_in(self):
        self.client.force_login(self.tenant)
        self.assertContains(self.client.get(reverse("properties:home")), reverse("reviews:my_reviews"))

    def test_deleting_a_user_removes_their_reviews(self):
        self.review(self.tenant, self.landlord)
        self.tenant.delete()
        self.assertEqual(Review.objects.count(), 0)


class StarsTag(TestCase):
    def test_star_icons(self):
        def count(html, name):
            return str(html).count(name)
        full = stars(5)
        self.assertEqual(count(full, "fa-solid fa-star filled"), 5)
        mid = stars(3.5)
        self.assertEqual((count(mid, "fa-solid fa-star filled"), count(mid, "star-half-stroke"), count(mid, "fa-regular")), (3, 1, 1))
        none = stars(None)
        self.assertEqual(count(none, "fa-regular fa-star"), 5)
        self.assertIn("4.5 out of 5", str(stars(4.4)))