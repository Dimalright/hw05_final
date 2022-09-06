import tempfile
import shutil

from django.test import Client, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from posts.models import Group, Post
from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.authorized_author = Client()
        cls.authorized_author.force_login(cls.author)

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post_form(self):
        """
        Валидная форма создает пост
        """
        post_count = Post.objects.count()
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
            'text': 'Тестовый пост',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile',
                kwargs={'username': self.author}
            )
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый пост',
                group=self.group.id,
            ).exists()
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_post_form(self):
        """
        Валидная форма редактирует пост
        """
        self.post = Post.objects.create(
            author=self.author,
            text='Тестовый пост 2',
            group=self.group
        )
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
        }
        response = self.authorized_author.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': '1'}
            ),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': '1'}
            ),
        )
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый пост 2',
                group=self.group.id
            ).exists()
        )
