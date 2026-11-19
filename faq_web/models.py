"""Django ORM-модели сервиса вопросов и ответов."""

from datetime import date

from django.db import models
from django.db.models.functions import Length
from django.urls import reverse
from django.utils.text import slugify
from unidecode import unidecode


class Section(models.Model):
    """Тематический раздел, в котором публикуются вопросы."""

    name = models.CharField(
        max_length=100,
        unique=True,
        null=False,
        blank=False,
        verbose_name="Название",
    )
    is_active = models.BooleanField(
        default=True,
        null=False,
        blank=False,
        verbose_name="Активен",
    )
    # description = models.TextField(
    #     blank=True,
    #     default="",
    #     verbose_name="Описание",
    # )

    class Meta:
        ordering = ["name"]
        verbose_name = "Раздел"
        verbose_name_plural = "Разделы"

    def __str__(self) -> str:
        return self.name


class User(models.Model):
    """Автор вопроса или ответа."""

    name = models.CharField(
        max_length=80,
        unique=True,
        null=False,
        blank=False,
        verbose_name="Имя",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        return self.name


class QuestionQuerySet(models.QuerySet):
    """Запросы вопросов по состоянию обсуждения."""

    def open(self):
        return self.filter(status=self.model.Status.OPEN)

    def closed(self):
        return self.filter(status=self.model.Status.CLOSED)


class QuestionManager(models.Manager.from_queryset(QuestionQuerySet)):
    """Менеджер вопросов с фильтрами по статусу."""


class Question(models.Model):
    """Вопрос FAQ с автором, разделом и статусом обсуждения."""

    class Status(models.TextChoices):
        OPEN = "open", "Открыт"
        CLOSED = "closed", "Закрыт"

    objects = QuestionManager()

    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,  # запрет удаления если есть ссылка
        related_name="questions",  # Имя обратной связи.
        null=False,
        blank=False,
        verbose_name="Раздел",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="authored_questions",
        null=False,
        blank=False,
        verbose_name="Автор",
    )
    title = models.CharField(
        max_length=200,
        null=False,
        blank=False,
        verbose_name="Заголовок",
    )
    slug = models.SlugField(
        max_length=220,
        unique=True,
        editable=False,
        verbose_name="URL-идентификатор",
    )
    text = models.TextField(
        null=False,
        blank=False,
        verbose_name="Текст",
    )
    image = models.ImageField(
        upload_to="questions/",
        blank=True,
        verbose_name="Изображение",
    )
    created_at = models.DateField(
        default=date.today,
        null=False,
        blank=False,
        verbose_name="Дата",
    )
    status = models.CharField(
        max_length=6,
        choices=Status.choices,  # Open / Closed
        default=Status.OPEN,
        null=False,
        blank=False,
        verbose_name="Статус",
    )

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            if self._state.adding:
                super().save(*args, **kwargs)
            suffix = f"-{self.pk}"
            base_slug = slugify(unidecode(self.title)) or "question"
            self.slug = f"{base_slug[:220 - len(suffix)]}{suffix}"
            super().save(update_fields=["slug"])
            return
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("faq:detail", kwargs={"slug": self.slug})


class Answer(models.Model):
    """Ответ пользователя на вопрос."""

    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,  # удаление связанных записей | PROTECT
        related_name="answers",
        null=False,
        blank=False,
        verbose_name="Вопрос",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="authored_answers",
        null=False,
        blank=False,
        verbose_name="Автор",
    )
    text = models.TextField(
        null=False,
        blank=False,
        verbose_name="Текст",
    )
    text_length = models.GeneratedField(
        expression=Length("text"),
        output_field=models.PositiveIntegerField(),
        db_persist=True,
        verbose_name="Длина текста",
    )
    created_at = models.DateField(
        default=date.today,
        null=False,
        blank=False,
        verbose_name="Дата",
    )

    class Meta:
        ordering = ["pk"]
        verbose_name = "Ответ"
        verbose_name_plural = "Ответы"

    def __str__(self) -> str:
        return f"Ответ на «{self.question}» от {self.author}"
