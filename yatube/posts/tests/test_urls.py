from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from posts.models import Post, Group

User = get_user_model()


class PostURLTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.POST_URL = '/posts/1/'
        cls.POSTS_EDIT = '/posts/1/edit/'
        cls.POSTS_EDIT_UNAUTH = '/auth/login/?next=/posts/1/edit/'

        cls.user = User.objects.create_user(username='user1')
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание группы',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group_id=cls.group.id
        )
        cls.templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/create/': 'posts/create_post.html',
            '/posts/1/edit/': 'posts/create_post.html',
            '/posts/1/': 'posts/post_detail.html',
            '/profile/user1/': 'posts/profile.html',
        }

    def test_create_and_edit_for_authorized_user(self):
        """Существующий URL-адрес доступен для не авторизованного пользователя,
        не существующий выдаёт ошибку 404.
        """
        adresses = ('/create/',
                    '/posts/1/edit/'
                    )
        for adress in adresses:
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_and_edit_for_anonym(self):
        """Страницы недоступные для неавторизованных пользователей
        перенаправляют пользователя на страницу логина.
        """
        adresses = {
            '/create/': '/auth/login/?next=/create/',
        }
        for adress, redirect_page in adresses.items():
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)
                self.assertRedirects(response, redirect_page)

    def test_edit_for_nonauthor(self):
        '''Страница /posts/post_id/edit/ недоступна не автору.'''
        user2 = User.objects.create_user(username='user2')
        authorized_client_2 = Client()
        authorized_client_2.force_login(user2)
        response = authorized_client_2.get(self.POSTS_EDIT)
        self.assertRedirects(response, self.POST_URL)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for address, template in self.templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
