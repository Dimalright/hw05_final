from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

POST_LIST: int = 15


class Post(models.Model):
    text = models.TextField(verbose_name='Текстовое поле')
    pub_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Автор'
    )
    group = models.ForeignKey(
        'Group',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='posts',
        verbose_name='Группа'
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    def __str__(post):
        return (f'{post.text[:POST_LIST]}')

    class Meta:
        ordering = ('-pub_date', )


class Group(models.Model):
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name='URL'
    )
    description = models.TextField(verbose_name='Описание')

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(
        'Post',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='comments',
        verbose_name='Комментируемый пост',
        help_text='Комментируемый пост',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор'
    )
    text = models.TextField(
        verbose_name='Комментарий',
        help_text='Введите комментарий к посту',
    )
    created = models.DateTimeField(
        "Дата добавления",
        auto_now_add=True,
        db_index=True
    )


class Follow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name="follower")
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following'
    )
