"""Django ORM-модели сервиса вопросов и ответов."""

from datetime import date

from django.db import models


class Section(models.Model):
    """Тематический раздел, в котором публикуются вопросы."""

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Название",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        ordering = ["name"]
        verbose_name = "Раздел"
        verbose_name_plural = "Разделы"

    def __str__(self) -> str:
        return self.name


class User(models.Model):
    """Автор вопроса или ответа."""

    name = models.CharField(max_length=80, unique=True, verbose_name="Имя")

    class Meta:
        ordering = ["name"]
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        return self.name


class Question(models.Model):
    """Вопрос FAQ с автором, разделом и статусом обсуждения."""

    class Status(models.TextChoices):
        OPEN = "open", "Открыт"
        CLOSED = "closed", "Закрыт"

    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="questions",
        verbose_name="Раздел",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="authored_questions",
        verbose_name="Автор",
    )
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    text = models.TextField(verbose_name="Текст")
    created_at = models.DateField(default=date.today, verbose_name="Дата")
    status = models.CharField(
        max_length=6,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name="Статус",
    )

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"

    def __str__(self) -> str:
        return self.title


class Answer(models.Model):
    """Ответ пользователя на вопрос."""

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Вопрос",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="authored_answers",
        verbose_name="Автор",
    )
    text = models.TextField(verbose_name="Текст")
    created_at = models.DateField(default=date.today, verbose_name="Дата")

    class Meta:
        ordering = ["pk"]
        verbose_name = "Ответ"
        verbose_name_plural = "Ответы"

    def __str__(self) -> str:
        return f"Ответ на «{self.question}» от {self.author}"
