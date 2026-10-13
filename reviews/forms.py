from django import forms

from .models import Review, ReviewReport
from .services import MAX_COMMENT_LENGTH


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(5, "5"), (4, "4"), (3, "3"), (2, "2"), (1, "1")],
        coerce=int,
        widget=forms.RadioSelect(attrs={"class": "star-radio"}),
        error_messages={"required": "Please choose a star rating.", "invalid_choice": "Please choose a rating from 1 to 5."},
    )
    comment = forms.CharField(
        required=False,
        max_length=MAX_COMMENT_LENGTH,
        widget=forms.Textarea(attrs={"rows": 4, "maxlength": MAX_COMMENT_LENGTH, "placeholder": "Tell others about your experience (optional)"}),
    )

    class Meta:
        model = Review
        fields = ["rating", "comment"]

    def clean_comment(self):
        return " ".join(self.cleaned_data["comment"].split()) if self.cleaned_data["comment"] else ""


class ReportForm(forms.ModelForm):
    class Meta:
        model = ReviewReport
        fields = ["reason", "note"]