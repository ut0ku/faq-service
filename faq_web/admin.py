"""Регистрация моделей FAQ в административной панели."""

from django.contrib import admin

from .models import Answer, Question, Section, User


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 1


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "author", "created_at", "status")
    inlines = (AnswerInline,)
    # Сортировка по дате создания
    ordering = ("-created_at", "-pk")
    # фильтр
    list_filter = ("status", "section")
    # поиск
    search_fields = ("title", "text", "author__name")
    # оптимизация Json (предзагрузка fk в одном запросе)
    list_select_related = ("section", "author")
    actions = ("close_questions",)

    @admin.action(description="Закрыть выбранные вопросы")
    def close_questions(self, request, queryset):
        closed_count = queryset.exclude(
            status=Question.Status.CLOSED
        ).update(status=Question.Status.CLOSED)
        self.message_user(request, f"Закрыто вопросов: {closed_count}.")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("question", "author", "created_at", "text_length")
    search_fields = ("text", "author__name", "question__title")
    list_select_related = ("question", "author")
