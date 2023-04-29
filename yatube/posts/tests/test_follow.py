from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from ..models import Post, Follow
from django.core.cache import cache


User = get_user_model()


class FollowViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создадим запись в БД для проверки доступности адреса task/test-slug/
        cls.user_follow = User.objects.create_user(username='auth_follow')
        cls.user_other = User.objects.create_user(username='auth_other')
        cls.user_author = User.objects.create_user(username='auth_author')
        cls.post = Post.objects.create(
            author=cls.user_other,
            text='IT SHOULD NOT BE IN LIST'
        )
        cls.post_author = Post.objects.create(
            author=cls.user_author,
            text='Текстовый текст',
        )
        cls.post_follow = Post.objects.create(
            author=cls.user_follow,
            text='111'
        )

    def setUp(self):
        cache.clear()
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем второй клиент
        self.authorized_follow = Client()
        self.authorized_other = Client()
        # Авторизуем пользователя
        self.authorized_follow.force_login(self.user_follow)
        self.authorized_other.force_login(self.user_other)

    def tearDown(self):
        cache.clear()

    def test_follow_unfollow_views(self):
        """Авторизованный пользователь может подписываться
          на других пользователей и удалять их из подписок."""
        # Подписываемся на автора
        self.authorized_follow.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user_author})
        )
        follow_index = self.authorized_follow.get(
            reverse('posts:follow_index',)
        )
        follow_count = len(follow_index.context['page_obj'])
        # Проверяем количество постов в ленте постов
        # (создано 2, один от автора)
        self.assertEqual(follow_count, 1)
        # Отписываемся от автора
        self.authorized_follow.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.user_author})
        )
        # Чистим кэш и сравниваем количество постов в подписках (ожидаем 0)
        cache.clear()
        follow_index_cleared = self.authorized_follow.get(
            reverse('posts:follow_index',)
        )
        follow_count_cleared = len(follow_index_cleared.context['page_obj'])
        self.assertEqual(follow_count_cleared, 0)

    def test_new_author_post(self):
        """Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех,
        кто не подписан."""
        # Подписываемся на автора
        self.authorized_follow.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user_author})
        )
        follow_index = self.authorized_follow.get(
            reverse('posts:follow_index',)
        )
        follow_count = len(follow_index.context['page_obj'])
        # Проверяем количество постов в ленте постов
        # (создано 2, один от автора)
        self.assertEqual(follow_count, 1)
        # Подписываемся на другого автора, чтобы избежать
        # ошибки NoneType при проверке далее
        self.authorized_other.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user_follow})
        )
        # Проверяем количество
        # постов в подписках, ожидаем 1
        follow_index_other = self.authorized_other.get(
            reverse('posts:follow_index',)
        )
        follow_count_other = len(follow_index_other.context['page_obj'])
        # Проверяем количество постов в подписках
        self.assertEqual(follow_count_other, 1)
        # Создаем новый пост автора и проверяем новое количество у каждого
        Post.objects.create(
            author=self.user_author,
            text='NEW TEXT',
        )
        follow_index_new = self.authorized_follow.get(
            reverse('posts:follow_index',)
        )
        follow_count_new = len(follow_index_new.context['page_obj'])
        # Проверяем количество постов в подписках у подписчикаы
        # (ожидаем 2)
        self.assertEqual(follow_count_new, 2)
        # Проверяем количество постов НЕ у подписчика в ленте подписок
        follow_index_other_new = self.authorized_other.get(
            reverse('posts:follow_index',)
        )
        follow_count_other_new = len(
            follow_index_other_new.context['page_obj'])
        # Проверяем количество постов в подписках (ожидаем все так же 1)
        self.assertEqual(follow_count_other_new, 1)

    def test_self_follow(self):
        """Нельзя подписаться на самого себя"""
        self.authorized_follow.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user_follow})
        )
        followers = Follow.objects.filter(user=self.user_follow)
        count = followers.count()
        self.assertEqual(count, 0)
