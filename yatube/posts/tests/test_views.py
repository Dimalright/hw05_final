import shutil
import tempfile

from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django import forms
from django.core.cache import cache

from posts.forms import PostForm
from posts.models import Post, Group, Comment, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='test_usr')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст поста',
            id=99999,
            group=cls.group,
            image=uploaded,
        )
        cls.templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}): (
                'posts/group_list.html'
            ),
            reverse('posts:profile', kwargs={'username': cls.post.author}): (
                'posts/profile.html'
            ),
            reverse('posts:post_detail', kwargs={'post_id': cls.post.id}): (
                'posts/post_detail.html'
            ),
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': cls.post.id}): (
                'posts/create_post.html'
            ),
        }
        cls.authorized_client = Client()
        cls.author = Client()
        cls.guest_client = Client()
        cls.author.force_login(cls.user)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_views_use_correct_template(self):
        for namespace, template in self.templates_pages_names.items():
            with self.subTest(template):
                response = self.author.get(namespace)
                self.assertTemplateUsed(response, template)

    def test_edit_or_create_post_page_show_correct_context(self):
        """Страницы создания и редактирования поста сформированы с правильным
        контекстом."""
        form_urls = (
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for url in form_urls:
            with self.subTest(value=url):
                response = self.author.get(url)
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context['form'].fields[value]
                        self.assertIsInstance(form_field, expected)

    def test_index_context_is_posts_list(self):
        """На главную страницу передаётся спиcок постов
        (Объект Paginator.page)"""
        response = self.guest_client.get(reverse("posts:index"))
        response_post = response.context.get('page_obj').object_list[0]
        post_image = response_post.image
        self.assertEqual(
            len(response.context.get("page_obj")), 1, "Не похоже на список!"
        )
        self.assertEqual(post_image, self.post.image)

    def test_group_list_recieves_list_filterd_by_group(self):
        """group_list доллжен содержать список постов,
        отфильтрованных по группе"""
        response = self.guest_client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
        )
        response_post = response.context.get('page_obj').object_list[0]
        post_image = response_post.image
        self.assertEqual(
            response.context.get("group"), self.group, "Группа не совпала"
        )
        self.assertEqual(post_image, self.post.image)

    def test_profile_recieves_posts_filterd_by_author(self):
        """profile должен получать список постов, отфильтрованный по автору"""
        response = self.guest_client.get(
            reverse(
                "posts:profile", kwargs={"username": self.user.get_username()}
            )
        )
        response_post = response.context.get('page_obj').object_list[0]
        post_image = response_post.image
        self.assertEqual(
            response.context.get("author"), self.user, "Автор не совпал"
        )
        self.assertEqual(post_image, self.post.image)

    def test_post_detail_has_1_post_selected_by_id(self):
        """post_detail должна содержать 1 пост, отобранный по id"""
        response = self.guest_client.get(
            reverse("posts:post_detail", kwargs={"post_id": self.post.id})
        )
        response_post = response.context.get('post')
        post_image = response_post.image
        self.assertEqual(
            response.context.get("post").id,
            self.post.id,
            "post_detail работает неправильно.",
        )
        self.assertEqual(post_image, self.post.image)

    def test_post_edit_has_form_with_post(self):
        """post_edit должен получать форму с постом, отобранным по id"""
        response = self.author.get(
            reverse("posts:post_edit", kwargs={"post_id": self.post.id})
        )
        self.assertEqual(
            response.context.get("post_id"),
            self.post.id,
            "Редактирование поста работает неправильно",
        )

    def test_post_create_has_form(self):
        """post_create должен получать форму создания поста"""
        response = self.author.get(reverse("posts:post_create"))
        self.assertTrue(
            isinstance(response.context.get("form"), PostForm),
            "Форма какая-то не та",
        )

    def test_group_hasnt_alien_posts(self):
        """Созданный пост не должен попасть в чужую группу"""
        Group.objects.create(
            title="Another group",
            slug="another_group_slug",
            description="another group description",
        )
        response = self.guest_client.get(
            reverse("posts:group_list", kwargs={"slug": "another_group_slug"})
        )
        another_group_post_list = response.context.get("page_obj").object_list
        self.assertTrue(self.post in another_group_post_list)

    def test_post_with_specified_group_is_shown_on_correct_pages(self):
        """Если при создании поста указать группу, то пост появляется на
        праивльных страницах."""
        group = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug-2',
            description='Тестовое описание 2'
        )
        post = Post.objects.create(
            author=self.user,
            text='Тестовый текст поста 2',
            id=999,
            group=group,
        )
        urls = (
            reverse('posts:index'),
            reverse(
                'posts:profile',
                kwargs={'username': post.author.username}
            ),
            reverse('posts:group_list', kwargs={'slug': group.slug}))
        for url in urls:
            with self.subTest(value=url):
                response = self.author.get(url)
                self.assertIn(post, response.context['page_obj'])
        other_group_response = self.author.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertIn(post, other_group_response.context['page_obj'])

    def test_index_cache(self):
        Post.objects.create(
            text='new-post-with-cache',
            author=self.user,
            group=self.group,
        )
        response = self.authorized_client.get('/')
        page = response.content.decode()
        self.assertNotIn('new-post-with-cache', page)
        cache.clear()
        response = self.authorized_client.get('/')
        page = response.content.decode()
        self.assertIn('new-post-with-cache', page)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super(PaginatorViewsTest, cls).setUpClass()
        cls.user = User.objects.create_user(username="HasNoName")
        cls.group = Group.objects.create(
            title="Test group",
            slug="test_group_slug",
            description="Test group description",
        )
        cls.posts = [Post(author=cls.user,
                     group=cls.group,
                     pub_date=timezone.now(),
                     text='Тестовый текст' + str(i)) for i in range(13)]
        Post.objects.bulk_create(cls.posts)
        cls.guest_client = Client()

    def test_first_page_contains_ten_records(self):
        """Paginator | index: На первой странице 10 постов"""
        response = self.guest_client.get(reverse("posts:index"))
        self.assertEqual(len(response.context["page_obj"]), 10)

    def test_second_page_contains_three_records(self):
        """Paginator  |  index: на второй странице 3 поста"""
        response = self.guest_client.get(reverse("posts:index") + "?page=2")
        self.assertEqual(len(response.context["page_obj"]), 3)

    def test_group_list_contains_ten_records(self):
        """Paginator  |  group_list: На первой странице 10 постов"""
        response = self.guest_client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
        )
        self.assertEqual(len(response.context["page_obj"]), 10, "Не десять!")

    def test_group_list_second_page_contains_three_records(self):
        """Paginator  |  group_list: На второй странице 3 поста"""
        response = self.guest_client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
            + "?page=2"
        )
        self.assertEqual(len(response.context["page_obj"]), 3, "Не три!")


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CommentViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.authorized_author = Client()
        cls.authorized_author.force_login(cls.author)
        cls.user = User.objects.create_user(username='user')
        cls.authorized_user = Client()
        cls.authorized_user.force_login(cls.user)
        cls.guest_client = Client()

        cls.post = Post.objects.create(
            author=cls.author,
            pub_date=datetime.now(),
            text='Тестовый пост',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый текст комментария',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_post_comment_is_shown_on_post_page(self):
        """После успешной отправки комментарий появляется на странице
        поста."""
        response = self.authorized_author.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertIn(self.comment, response.context['comments'])

    def test_comment_authorized_user_can(self):
        """
        Авторизованный юзер может комментить
        """
        self.authorized_user.post(reverse(
            'posts:add_comment',
            kwargs={'post_id': self.post.id}
        ),
            {'text': 'Тестовый комментарий', },
            follow=True
        )
        response = self.authorized_user.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}
        ),
        )
        self.assertContains(response, 'Тестовый комментарий')

    def test_comment_unauthorized_user_cant(self):
        """
        Неавторизованный юзер комментить не может
        """
        self.guest_client.post(reverse(
            'posts:add_comment',
            kwargs={'post_id': self.post.id}
        ),
            {'text': '2 Тестовый комментарий 2', },
            follow=True
        )
        response = self.guest_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}
        ),
        )
        self.assertNotContains(response, '2 Тестовый комментарий 2')


class FollowViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='User1'
        )
        cls.user_2 = User.objects.create_user(
            username='User2'
        )
        cls.follow = Follow.objects.create(
            author=cls.user,
            user=cls.user_2
        )
        cls.group_1 = Group.objects.create(
            title='Название группы для теста_1',
            slug='test-slug_1',
            description='Описание группы для теста_1'
        )
        cls.group_2 = Group.objects.create(
            title='Название группы для теста_2',
            slug='test-slug_2',
            description='Описание группы для теста_2'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текст поста для теста',
            group=cls.group_1,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_follow_another_user(self):
        """Авторизованный пользователь,
        может подписываться на других пользователей"""
        follow_count = Follow.objects.count()
        self.authorized_client.get(reverse('posts:profile_follow',
                                           kwargs={'username': self.user_2}))
        self.assertTrue(Follow.objects.filter(user=self.user,
                                              author=self.user_2).exists())
        self.assertEqual(Follow.objects.count(), follow_count + 1)

    def test_unfollow_another_user(self):
        """Авторизованный пользователь
        может удалять других пользователей из подписок"""
        Follow.objects.create(user=self.user, author=self.user_2)
        follow_count = Follow.objects.count()
        self.assertTrue(Follow.objects.filter(user=self.user,
                                              author=self.user_2).exists())
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.user_2}
            )
        )
        self.assertFalse(
            Follow.objects.filter(
                user=self.user,
                author=self.user_2
            ).exists()
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)

    def test_new_post_follow(self):
        """ Новая запись пользователя будет в ленте у тех кто на него
            подписан.
        """
        following = User.objects.create(username='following')
        Follow.objects.create(user=self.user, author=following)
        post = Post.objects.create(author=following, text=self.post.text)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertIn(post, response.context['page_obj'].object_list)

    def test_new_post_unfollow(self):
        """ Новая запись пользователя не будет у тех кто не подписан на него.
        """
        self.client.logout()
        User.objects.create_user(
            username='somobody_temp',
            password='pass'
        )
        self.client.login(username='somobody_temp')
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotIn(
            self.post.text,
            response.context['page_obj'].object_list
        )
