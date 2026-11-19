"""Django forms for filtering questions and creating FAQ entries."""

from django import forms
from django.db.models import Q

from .models import Question, Section

MAX_QUESTION_IMAGE_SIZE = 5 * 1024 * 1024


class QuestionFilterForm(forms.Form):
    """Validate question-list filters supplied through GET parameters."""

    date = forms.DateField(
        required=False,
        label="Дата вопроса",
        error_messages={"invalid": "Укажите корректную дату."},
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "id": "question-date",
            }
        ),
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.filter(is_active=True).order_by("name"),
        required=False,
        label="Раздел",
        empty_label="Все разделы",
        to_field_name="name",
        widget=forms.Select(
            attrs={"class": "form-select", "id": "question-section"}
        ),
    )
    author = forms.CharField(
        required=False,
        label="Автор",
        widget=forms.TextInput(
            attrs={"class": "form-control", "id": "question-author"}
        ),
    )
    q = forms.CharField(
        required=False,
        label="Поиск",
        widget=forms.TextInput(
            attrs={"class": "form-control", "id": "question-search"}
        ),
    )
    sort = forms.ChoiceField(
        required=False,
        label="Сортировка",
        choices=(
            ("date", "По дате"),
            ("title", "По заголовку"),
            ("section", "По разделу"),
            ("author", "По автору"),
        ),
        widget=forms.Select(
            attrs={"class": "form-select", "id": "question-sort"}
        ),
    )


class QuestionContentForm(forms.ModelForm):
    """Validate the editable content shared by create and edit forms."""

    section = forms.ModelChoiceField(
        queryset=Section.objects.none(),
        label="Раздел",
        empty_label="Выберите раздел",
        to_field_name="name",
        widget=forms.Select(
            attrs={"class": "form-select", "id": "question-section"}
        ),
    )

    class Meta:
        model = Question
        fields = ("section", "title", "text", "image")
        labels = {
            "title": "Заголовок",
            "text": "Текст вопроса",
            "image": "Изображение к вопросу",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "id": "question-title",
                }
            ),
            "text": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "id": "question-text",
                    "rows": 5,
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sections = Section.objects.filter(is_active=True)
        if self.instance.pk:
            sections = Section.objects.filter(
                Q(is_active=True) | Q(pk=self.instance.section_id)
            )
        self.fields["section"].queryset = sections.order_by("name")

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if len(title) < 5:
            raise forms.ValidationError(
                "Заголовок слишком короткий (минимум 5 символов)"
            )
        return title

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > MAX_QUESTION_IMAGE_SIZE:
            raise forms.ValidationError(
                "Размер изображения не должен превышать 5 МБ."
            )
        return image


class QuestionCreateForm(QuestionContentForm):
    """Validate and save the fields users may set when creating a question."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["author"] = forms.CharField(
            label="Ваше имя",
            max_length=80,
            widget=forms.TextInput(
                attrs={
                    "class": "form-control",
                    "id": "question-author",
                }
            ),
        )
        self.order_fields(("author", "section", "title", "text"))


class QuestionUpdateForm(QuestionContentForm):
    """Edit question content without changing its author or status."""
