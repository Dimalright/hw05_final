from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from .forms import PostForm, CommentForm
from .models import Post, Group, User, Follow
from .utils import page


def index(request):
    posts = Post.objects.select_related('group')
    context = {
        'page_obj': page(request, posts)
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = Post.objects.select_related('group')
    context = {
        'group': group,
        'page_obj': page(request, posts)
    }
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    post_author = Post.objects.filter(author=author)
    if request.user.is_authenticated:
        follow = Follow.objects.filter(
            user=request.user.id,
            author=author.id
        ).exists()
    else:
        follow = False
    context = {
        'author': author,
        'page_obj': page(request, post_author),
        'follow': follow,

    }
    return render(request, template, context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    author = get_object_or_404(User, username=post.author)
    form = CommentForm(request.POST or None)
    comments = post.comments.all()
    context = {
        'post': post,
        'author': author,
        'form': form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    form = PostForm(request.POST or None,
                    files=request.FILES or None
                    )
    context = {'form': form}
    if request.method == 'POST' and form.is_valid():
        instance_form = form.save(commit=False)
        instance_form.author = request.user
        instance_form.save()
        username = request.user.username
        return redirect(reverse('posts:profile', args=[username]))
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    template = 'posts/create_post.html'
    post = get_object_or_404(Post, pk=post_id)
    if post.author == request.user:
        form = PostForm(request.POST or {'text': post.text,
                        'group': post.group}, files=request.FILES or None,
                        instance=post
                        )
        if request.method == 'POST' and form.is_valid():
            post.text = form.cleaned_data['text']
            post.group = form.cleaned_data['group']
            form = PostForm(request.POST, instance=post)
            post.save()
            return redirect('posts:post_detail', post_id)
        context = {'form': form,
                   'post_id': post_id,
                   'is_edit': True,
                   }
        return render(request, template, context)
    return redirect('posts:post_detail', post_id)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    context = {
        'page_obj': page(request, post_list)
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    if author != user:
        Follow.objects.get_or_create(
            user=user, author=author
        )
    return redirect('posts:profile', username=author.username)


@login_required
def profile_unfollow(request, username):
    user = get_object_or_404(User, username=username)
    unfollow, _ = Follow.objects.get_or_create(
        user=request.user, author=user)
    unfollow.delete()
    return redirect('posts:profile', username)
