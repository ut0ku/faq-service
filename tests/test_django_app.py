"""Проверки страниц Django-приложения FAQ."""

from io import BytesIO
import random
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from faq_web.models import Answer, Question, Section, User
from storage import load_data


class FaqPagesTests(TestCase):
    """Проверить ORM-модели и основные маршруты FAQ."""

    @classmethod
    def setUpTestData(cls):
        sections, questions = load_data(
            settings.BASE_DIR / "data" / "faq.json"
        )
        section_models = {
            section.name: Section.objects.create(
                name=section.name,
                is_active=section.is_active,
            )
            for section in sections
        }
        user_names = {
            question.author.name
            for question in questions
        }
        user_names.update(
            answer.author.name
            for question in questions
            for answer in question.answers
        )
        users = {
            name: User.objects.create(name=name)
            for name in user_names
        }
        for question in questions:
            question_model = Question.objects.create(
                pk=question.id,
                section=section_models[question.section],
                author=users[question.author.name],
                title=question.title,
                text=question.text,
                created_at=question.created_at,
                status=question.status,
            )
            Answer.objects.bulk_create(
                [
                    Answer(
                        question=question_model,
                        author=users[answer.author.name],
                        text=answer.text,
                        created_at=answer.created_at,
                    )
                    for answer in question.answers
                ]
            )

    def setUp(self):
        self.client = Client()

    def test_homepage_shows_service_summary(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Сервис вопросов и ответов")
        self.assertContains(response, "Перейти к вопросам")

    def test_question_list_links_to_dynamic_detail_pages(self):
        response = self.client.get("/faq/")
        question = Question.objects.get(pk=1)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Как преобразовать строку в число?")
        self.assertContains(response, f'href="{question.get_absolute_url()}"')

    def test_question_slugs_are_unique_and_open_their_detail_pages(self):
        question = Question.objects.get(pk=1)
        duplicate = Question.objects.create(
            section=question.section,
            author=question.author,
            title=question.title,
            text="Похожий вопрос",
        )

        self.assertNotEqual(question.slug, duplicate.slug)
        self.assertEqual(duplicate.status, Question.Status.OPEN)
        self.assertEqual(
            self.client.get(question.get_absolute_url()).status_code,
            200,
        )

    def test_question_list_can_filter_by_creation_date(self):
        response = self.client.get("/faq/", {"date": "2026-10-01"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python · ivan_petrov")
        self.assertNotContains(response, "Как преобразовать строку в число?")

    def test_question_list_filters_by_section_author_and_search(self):
        response = self.client.get(
            "/faq/",
            {
                "date": "2026-10-01",
                "section": "Python",
                "author": "ivan",
                "q": "Python",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python · ivan_petrov")
        self.assertNotContains(response, "Как преобразовать строку в число?")

    def test_question_list_sorts_and_handles_invalid_parameters(self):
        response = self.client.get("/faq/", {"sort": "title"})

        self.assertEqual(response.context["questions"][0].pk, 3)
        invalid_sort = self.client.get("/faq/", {"sort": "not-a-field"})
        self.assertEqual(invalid_sort.context["sort"], "date")
        self.assertIn("sort", invalid_sort.context["filter_form"].errors)
        invalid_date = self.client.get("/faq/", {"date": "not-a-date"})
        self.assertContains(invalid_date, "Укажите корректную дату.")
        self.assertContains(invalid_date, "Пока нет вопросов.")
        invalid_section = self.client.get(
            "/faq/",
            {"section": "Несуществующий раздел"},
        )
        self.assertEqual(invalid_section.status_code, 200)
        self.assertIn("section", invalid_section.context["filter_form"].errors)

    def test_pagination_keeps_filters_and_sorting(self):
        author = User.objects.get(name="ivan_petrov")
        section = Section.objects.get(name="Python")
        for number in range(6):
            Question.objects.create(
                section=section,
                author=author,
                title=f"Дополнительный вопрос {number}",
                text="Тестовый текст",
                created_at="2026-10-11",
            )

        response = self.client.get(
            "/faq/",
            {
                "section": "Python",
                "author": "ivan",
                "sort": "title",
                "page": "2",
            },
        )

        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertContains(
            response,
            'href="?section=Python&amp;author=ivan&amp;sort=title&amp;page=1"',
        )
        invalid_page = self.client.get("/faq/", {"page": "abc"})
        self.assertEqual(invalid_page.context["page_obj"].number, 1)

    def test_question_detail_shows_answers(self):
        question = Question.objects.get(pk=1)
        response = self.client.get(question.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Как из str получить int?")
        self.assertContains(response, "Используйте функцию int()")

    def test_section_page_lists_sections_and_questions(self):
        sections_response = self.client.get("/faq/sections/")

        self.assertEqual(sections_response.status_code, 200)
        self.assertContains(sections_response, "Тематические разделы")
        self.assertContains(
            sections_response,
            'href="/faq/sections/?section=Python"',
        )

        questions_response = self.client.get(
            "/faq/sections/",
            {"section": "Python"},
        )
        self.assertEqual(questions_response.status_code, 200)
        self.assertContains(
            questions_response,
            "Вопросы раздела «Python»",
        )
        self.assertContains(
            questions_response,
            "Как преобразовать строку в число?",
        )

    def test_section_page_handles_empty_sections(self):
        Section.objects.create(name="Новый раздел")

        response = self.client.get(
            "/faq/sections/",
            {"section": "Новый раздел"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "В этом разделе пока нет вопросов.")

    def test_models_expose_related_objects_and_reverse_relations(self):
        question = Question.objects.select_related(
            "section",
            "author",
        ).get(pk=1)

        self.assertEqual(question.section.name, "Python")
        self.assertEqual(question.author.name, "maria_smirnova")
        self.assertEqual(question.answers.count(), 1)
        self.assertEqual(question.author.authored_questions.count(), 1)

    def test_question_queryset_filters_open_and_closed_questions(self):
        self.assertEqual(
            set(Question.objects.open().values_list("pk", flat=True)),
            {2, 4, 5},
        )
        self.assertEqual(
            set(Question.objects.closed().values_list("pk", flat=True)),
            {1, 3},
        )

    def test_answer_text_length_is_computed_and_updated_by_database(self):
        answer = Answer.objects.get(question_id=1)

        self.assertEqual(answer.text_length, len(answer.text))

        Answer.objects.filter(pk=answer.pk).update(text="Короткий ответ")
        answer.refresh_from_db()
        self.assertEqual(answer.text_length, len("Короткий ответ"))

    def test_admin_can_update_and_delete_questions(self):
        admin_user = get_user_model().objects.create_superuser(
            username="faq_admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("admin:faq_web_question_changelist"),
            {
                "action": "close_questions",
                "_selected_action": ["2"],
            },
        )

        self.assertEqual(response.status_code, 302)
        question = Question.objects.get(pk=2)
        self.assertEqual(question.status, Question.Status.CLOSED)
        Answer.objects.filter(question=question).delete()

        response = self.client.post(
            reverse("admin:faq_web_question_delete", args=[question.pk]),
            {"post": "yes"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Question.objects.filter(pk=question.pk).exists())

    def test_staff_can_edit_question_without_changing_author_or_status(self):
        question = Question.objects.get(pk=2)
        original_author = question.author
        staff_user = get_user_model().objects.create_user(
            username="faq_staff",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(staff_user)

        response = self.client.get(reverse("faq:edit", args=[question.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, question.title)
        response = self.client.post(
            reverse("faq:edit", args=[question.slug]),
            {
                "section": question.section.name,
                "title": "Изменённый заголовок",
                "text": "Изменённый текст вопроса",
            },
        )

        self.assertRedirects(response, question.get_absolute_url())
        question.refresh_from_db()
        self.assertEqual(question.title, "Изменённый заголовок")
        self.assertEqual(question.text, "Изменённый текст вопроса")
        self.assertEqual(question.author, original_author)
        self.assertEqual(question.status, Question.Status.OPEN)

    def test_non_staff_cannot_edit_or_close_questions(self):
        question = Question.objects.get(pk=2)

        edit_response = self.client.get(
            reverse("faq:edit", args=[question.slug])
        )
        close_response = self.client.post(
            reverse("faq:close", args=[question.slug])
        )

        self.assertEqual(edit_response.status_code, 302)
        self.assertEqual(close_response.status_code, 302)
        question.refresh_from_db()
        self.assertEqual(question.status, Question.Status.OPEN)

    def test_staff_edit_and_close_forms_require_csrf_tokens(self):
        question = Question.objects.get(pk=2)
        staff_user = get_user_model().objects.create_user(
            username="faq_csrf_staff",
            password="test-password",
            is_staff=True,
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(staff_user)

        edit_response = client.post(
            reverse("faq:edit", args=[question.slug]),
            {
                "section": question.section.name,
                "title": question.title,
                "text": question.text,
            },
        )
        close_response = client.post(
            reverse("faq:close", args=[question.slug])
        )

        self.assertEqual(edit_response.status_code, 403)
        self.assertEqual(close_response.status_code, 403)
        question.refresh_from_db()
        self.assertEqual(question.status, Question.Status.OPEN)

    def test_staff_can_close_questions_only_with_post(self):
        question = Question.objects.get(pk=2)
        staff_user = get_user_model().objects.create_user(
            username="faq_moderator",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(staff_user)

        get_response = self.client.get(
            reverse("faq:close", args=[question.slug])
        )
        self.assertEqual(get_response.status_code, 405)
        question.refresh_from_db()
        self.assertEqual(question.status, Question.Status.OPEN)

        response = self.client.post(
            reverse("faq:close", args=[question.slug])
        )

        self.assertRedirects(response, question.get_absolute_url())
        question.refresh_from_db()
        self.assertEqual(question.status, Question.Status.CLOSED)
        self.assertNotContains(
            self.client.get(question.get_absolute_url()),
            "Закрыть вопрос",
        )

    def test_edit_and_close_return_404_for_missing_question(self):
        staff_user = get_user_model().objects.create_user(
            username="faq_staff_missing",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(staff_user)

        edit_response = self.client.get(
            reverse("faq:edit", args=["unknown-question"])
        )
        close_response = self.client.post(
            reverse("faq:close", args=["unknown-question"])
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(close_response.status_code, 404)

    def test_statistics_page_shows_question_and_answer_counts(self):
        response = self.client.get("/faq/statistics/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Статистика FAQ")
        self.assertContains(response, "Всего вопросов: 5")
        self.assertContains(response, "Всего ответов: 5")
        self.assertContains(response, "Открытых вопросов: 3")
        self.assertContains(response, "Закрытых вопросов: 2")
        self.assertContains(response, "Python")

    def test_shared_template_context_contains_service_summary(self):
        response = self.client.get("/")

        self.assertEqual(response.context["site_name"], "FAQ Service")
        self.assertEqual(response.context["open_questions_count"], 3)
        self.assertContains(response, "Вопросы")
        self.assertContains(response, ">3</span>")

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_missing_section_uses_custom_404_page(self):
        response = self.client.get(
            "/faq/sections/",
            {"section": "Несуществующий раздел"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Страница не найдена", status_code=404)

    def test_user_can_create_question(self):
        response = self.client.post(
            "/faq/new/",
            {
                "author": "  alex  ",
                "section": "Python",
                "title": "Новый вопрос",
                "text": "Текст нового вопроса",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRegex(response.url, r"^/faq/[a-z0-9-]+/$")
        question_response = self.client.get(response.url)
        self.assertContains(question_response, "Новый вопрос")
        self.assertContains(question_response, "alex")
        question = Question.objects.get(slug=response.url.split("/")[-2])
        self.assertEqual(question.status, Question.Status.OPEN)

    def test_user_can_upload_image_with_question(self):
        image_buffer = BytesIO()
        Image.new("RGB", (10, 10), color="blue").save(
            image_buffer,
            format="PNG",
        )
        image = SimpleUploadedFile(
            "question.png",
            image_buffer.getvalue(),
            content_type="image/png",
        )

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    "/faq/new/",
                    {
                        "author": "alex",
                        "section": "Python",
                        "title": "Вопрос с изображением",
                        "text": "Текст вопроса с изображением",
                        "image": image,
                    },
                )

                self.assertEqual(response.status_code, 302)
                question = Question.objects.get(
                    title="Вопрос с изображением"
                )
                self.assertTrue(question.image.name.startswith("questions/"))
                self.assertTrue(
                    question.image.storage.exists(question.image.name)
                )
                detail_response = self.client.get(question.get_absolute_url())
                self.assertContains(detail_response, question.image.url)

    def test_question_image_must_be_an_image_and_within_size_limit(self):
        invalid_image = SimpleUploadedFile(
            "not-an-image.png",
            b"not an image",
            content_type="image/png",
        )
        invalid_response = self.client.post(
            "/faq/new/",
            {
                "author": "alex",
                "section": "Python",
                "title": "Некорректное изображение",
                "text": "Текст вопроса",
                "image": invalid_image,
            },
        )
        self.assertEqual(invalid_response.status_code, 400)
        self.assertIn("image", invalid_response.context["form"].errors)

        image_buffer = BytesIO()
        image_size = (1400, 1300)
        image_bytes = random.Random(0).randbytes(
            image_size[0] * image_size[1] * 3
        )
        Image.frombytes("RGB", image_size, image_bytes).save(
            image_buffer, format="PNG"
        )
        large_image = SimpleUploadedFile(
            "large.png",
            image_buffer.getvalue(),
            content_type="image/png",
        )
        self.assertGreater(len(large_image), 5 * 1024 * 1024)
        large_response = self.client.post(
            "/faq/new/",
            {
                "author": "alex",
                "section": "Python",
                "title": "Слишком большое изображение",
                "text": "Текст вопроса",
                "image": large_image,
            },
        )
        self.assertEqual(large_response.status_code, 400)
        self.assertIn("image", large_response.context["form"].errors)

    def test_question_creation_form_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get("/faq/new/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        response = client.post(
            "/faq/new/",
            {
                "author": "alex",
                "section": "Python",
                "title": "Новый вопрос",
                "text": "Текст нового вопроса",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_invalid_question_is_not_saved(self):
        response = self.client.post(
            "/faq/new/",
            {
                "author": "alex",
                "section": "Python",
                "title": "Нет",
                "text": "Текст",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Заголовок слишком короткий",
            status_code=400,
        )
        self.assertIn("title", response.context["form"].errors)
        list_response = self.client.get("/faq/")
        self.assertNotContains(list_response, "Нет")

    def test_user_can_answer_open_question(self):
        Question.objects.filter(pk=1).update(status=Question.Status.OPEN)

        question = Question.objects.get(pk=1)
        response = self.client.post(
            question.get_absolute_url(),
            {"author": "  alex  ", "text": "Новый ответ"},
        )

        self.assertRedirects(response, question.get_absolute_url())
        detail_response = self.client.get(question.get_absolute_url())
        self.assertContains(detail_response, "Новый ответ")
        self.assertContains(detail_response, "alex")

    def test_closed_question_rejects_new_answer(self):
        question = Question.objects.get(pk=3)
        response = self.client.post(
            question.get_absolute_url(),
            {"author": "alex", "text": "Ответ к закрытому вопросу"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Вопрос закрыт",
            status_code=400,
        )
        detail_response = self.client.get(question.get_absolute_url())
        self.assertNotContains(detail_response, "Ответ к закрытому вопросу")

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_missing_question_uses_custom_404_page(self):
        response = self.client.get("/faq/unknown-question/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Страница не найдена", status_code=404)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_unknown_url_uses_custom_404_page(self):
        response = self.client.get("/unknown/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "На главную", status_code=404)
