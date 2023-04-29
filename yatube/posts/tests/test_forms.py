import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from ..models import Post, Group, Comment
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

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
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текстовый текст',
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """В БД создается новая запись"""
        posts_count = Post.objects.count()
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
        form_data = {
            'text': 'New text',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        summ_post = 1
        self.assertRedirects(
            response,
            reverse('posts:profile',
                    kwargs={'username': 'auth'})
        )
        self.assertEqual(Post.objects.count(), posts_count + summ_post)
        # Проверяем, существует ли в БД пост с картинкой
        self.assertTrue(Post.objects.filter(
            text='New text',
            image='posts/small.gif',
        ).exists())

    def test_post_edit(self):
        """Валидная форма редактирует пост в БД"""
        form_data = {
            'text': 'New text 1',
            'group': self.group.id,
        }
        self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertTrue(Post.objects.filter(
            text='New text 1'
        ).exists())

    def test_authorized_only_comment(self):
        """Только авторизованный пользователь может оставлять комментарии"""
        response = self.guest_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': self.post.id}),
            data={'text': 'Test comment'},
            follow=True
        )
        self.assertRedirects(response,
                             '/auth/login/?next=/posts/1/comment/'
                             )

    def test_create_comment(self):
        """Новый комментарий создается в БД"""
        comments = Comment.objects.filter(post_id=self.post.id)
        comments_count = comments.count()
        self.authorized_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': self.post.id}),
            data={'text': 'Test comment'},
            follow=True,
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
