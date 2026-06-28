from math import ceil


PAGE_SIZE_CHOICES = {10, 20, 50}


def get_page_params(request):
    try:
        page = max(int(request.query_params.get("page", 1)), 1)
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.query_params.get("page_size", 20))
    except (TypeError, ValueError):
        page_size = 20
    if page_size not in PAGE_SIZE_CHOICES:
        page_size = 20
    return page, page_size


def paginate_queryset(request, queryset):
    page, page_size = get_page_params(request)
    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    meta = {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": ceil(total / page_size) if total else 0,
    }
    return queryset[start:end], meta
