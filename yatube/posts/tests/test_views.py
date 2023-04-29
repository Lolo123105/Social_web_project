import shutil
import time
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from ..models import Post, Group
from django import forms
from django.conf import settings
from django.core.cache import cache

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД для проверки доступности адреса task/test-slug/
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='test-title',
            slug='test-slug',
            description='test-desc',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текстовый текст',
            group=cls.group,
            image=uploaded
        )

    def setUp(self):
        cache.clear()
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(PostsViewsTests.user)

    def tearDown(self):
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_templates(self):
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug':
                            PostsViewsTests.group.slug}):
                                'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username':
                            PostsViewsTests.user.username}):
                                'posts/profile.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    kwargs={'post_id':
                            PostsViewsTests.post.id}):
                                'posts/create_post.html',
            reverse('posts:post_detail',
                    kwargs={'post_id':
                            PostsViewsTests.post.id}):
                                'posts/post_detail.html',

        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_create_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        # Словарь ожидаемых типов полей формы:
        # указываем, объектами какого класса должны быть поля формы
        form_fields = {
            # При создании формы поля модели типа TextField
            # преобразуются в CharField с виджетом forms.Textarea
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }

        # Проверяем, что типы полей формы
        # в словаре context соответствуют ожиданиям
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                # Проверяет, что поле формы является экземпляром
                # указанного класса
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={'post_id':
                            PostsViewsTests.post.id}))
        # Словарь ожидаемых типов полей формы:
        # указываем, объектами какого класса должны быть поля формы
        form_fields = {
            # При создании формы поля модели типа TextField
            # преобразуются в CharField с виджетом forms.Textarea
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField
        }

        # Проверяем, что типы полей формы
        # в словаре context соответствуют ожиданиям
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                # Проверяет, что поле формы является экземпляром
                # указанного класса
                self.assertIsInstance(form_field, expected)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id':
                            PostsViewsTests.post.id}))
        form_field = response.context.get('post').text
        form_image = response.context.get('post').image
        # Проверяет, что поле формы является экземпляром
        # указанного класса
        self.assertEqual(form_field, 'Текстовый текст')
        self.assertEqual(form_image, 'posts/small.gif')

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:index',))
        # Взяли первый элемент из списка и проверили, что его содержание
        # совпадает с ожидаемым
        first_object = response.context['page_obj'][0]
        task_text_0 = first_object.text
        task_author_0 = first_object.author
        task_group_0 = first_object.group
        task_image_0 = first_object.image
        self.assertEqual(task_text_0, 'Текстовый текст')
        self.assertEqual(task_author_0, PostsViewsTests.user)
        self.assertEqual(task_author_0, PostsViewsTests.user)
        self.assertEqual(task_group_0, PostsViewsTests.group)
        self.assertEqual(task_image_0, 'posts/small.gif')

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug':
                            PostsViewsTests.group.slug}))
        # Взяли первый элемент из списка и проверили, что его содержание
        # совпадает с ожидаемым
        first_object = response.context['page_obj'][0]
        task_text_0 = first_object.text
        task_author_0 = first_object.author
        task_group_0 = first_object.group
        task_image_0 = first_object.image
        self.assertEqual(task_text_0, 'Текстовый текст')
        self.assertEqual(task_author_0, PostsViewsTests.user)
        self.assertEqual(task_author_0, PostsViewsTests.user)
        self.assertEqual(task_group_0, PostsViewsTests.group)
        self.assertEqual(task_image_0, 'posts/small.gif')

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username':
                            PostsViewsTests.user.username}))
        # Взяли первый элемент из списка и проверили, что его содержание
        # совпадает с ожидаемым
        first_object = response.context['page_obj'][0]
        task_text_0 = first_object.text
        task_author_0 = first_object.author
        task_group_0 = first_object.group
        task_image_0 = first_object.image
        self.assertEqual(task_text_0, 'Текстовый текст')
        self.assertEqual(task_author_0, PostsViewsTests.user)
        self.assertEqual(task_author_0, PostsViewsTests.user)
        self.assertEqual(task_group_0, PostsViewsTests.group)
        self.assertEqual(task_image_0, 'posts/small.gif')

    def test_index_cache(self):
        """Проверка работы кэша на главной странице"""
        # Создаем новую запись в БД
        new_post = Post.objects.create(
            author=self.user,
            text='Текстовый текст 1'
        )
        # Переходим на главную страницу и берем текст
        # первого поста (ожидаем текст нового поста)
        response = self.authorized_client.get(
            reverse('posts:index',))
        first_object = response.context['page_obj'][0]
        text_0 = first_object.text
        # Удаляем новый пост и ждем обновления кэша страницы
        Post.objects.get(id=new_post.id).delete()
        time.sleep(20)
        # Обновляем страницу и берем текст первого в списке поста
        response_new = self.authorized_client.get(
            reverse('posts:index',))
        sec_object = response_new.context['page_obj'][0]
        text_1 = sec_object.text
        # Ожидаем, что тексты будут разные
        self.assertNotEqual(text_0, text_1)
