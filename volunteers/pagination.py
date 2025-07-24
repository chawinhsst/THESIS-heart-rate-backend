from rest_framework.pagination import PageNumberPagination

class CustomPageNumberPagination(PageNumberPagination):
    # Allows the frontend to specify the page size with a URL parameter, e.g., ?page_size=25
    page_size_query_param = 'page_size'
    # Sets a reasonable upper limit for how many items can be requested at once
    max_page_size = 1000