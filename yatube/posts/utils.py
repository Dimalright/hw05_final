from django.core.paginator import Paginator


NUMBER: int = 10


def page(request, posts):
    paginator = Paginator(posts, NUMBER)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
