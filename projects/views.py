from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView
from django.core.cache import cache
from .models import Project, ProjectCategory, ProjectImage, ProjectVideo, ProjectDocument, ProjectLike


# ==================== دوال مساعدة ====================

def get_client_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    return x.split(',')[0] if x else request.META.get('REMOTE_ADDR')


def get_featured_projects():
    cached = cache.get('featured_projects')
    if not cached:
        cached = list(Project.objects.filter(
            is_active=True, is_featured=True
        ).select_related('category').order_by('-created_at')[:6])
        cache.set('featured_projects', cached, 60 * 30)
    return cached


def get_recent_projects(limit=6):
    cached = cache.get(f'recent_projects_{limit}')
    if not cached:
        cached = list(Project.objects.filter(
            is_active=True
        ).select_related('category').order_by('-created_at')[:limit])
        cache.set(f'recent_projects_{limit}', cached, 60 * 15)
    return cached


def get_popular_projects(limit=6):
    cached = cache.get(f'popular_projects_{limit}')
    if not cached:
        cached = list(Project.objects.filter(
            is_active=True
        ).select_related('category').order_by('-views_count', '-likes_count')[:limit])
        cache.set(f'popular_projects_{limit}', cached, 60 * 60)
    return cached


def get_project_statistics():
    cached = cache.get('project_statistics')
    if not cached:
        qs = Project.objects.filter(is_active=True)
        cached = {
            'total_projects':       qs.count(),
            'completed_projects':   qs.filter(status='completed').count(),
            'active_projects':      qs.filter(status='active').count(),
            'total_beneficiaries':  qs.aggregate(total=Sum('beneficiaries_count'))['total'] or 0,
            'total_raised':         qs.aggregate(total=Sum('raised_amount'))['total'] or 0,
        }
        cache.set('project_statistics', cached, 60 * 60)
    return cached


# ==================== Views الرئيسية ====================




def project_detail(request, slug):
    """صفحة تفاصيل المشروع"""
    try:
        project = get_object_or_404(
            Project.objects.select_related('category'), slug=slug, is_active=True
        )

        if not request.session.get(f'viewed_project_{project.id}'):
            project.increment_views()
            request.session[f'viewed_project_{project.id}'] = True

        related_projects = Project.objects.filter(
            category=project.category, is_active=True
        ).exclude(id=project.id).select_related('category').order_by('-views_count')[:6]

        user_ip  = get_client_ip(request)
        context  = {
            'project':          project,
            'images':           project.images.filter(is_active=True).order_by('order'),
            'videos':           project.videos.filter(is_active=True).order_by('order'),
            'documents':        project.documents.filter(is_active=True, is_public=True).order_by('-created_at'),
            'related_projects': related_projects,
            'user_liked':       ProjectLike.objects.filter(project=project, ip_address=user_ip).exists(),
            'page_title':       project.title_ar,
            'meta_description': project.meta_description_ar or project.summary_ar,
        }
        return render(request, 'projects/project_detail.html', context)
    except Exception:
        return redirect('projects:project_not_found')

def all_projects(request):
    """صفحة جميع المشاريع مع فلترة وبحث"""
    search        = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '')
    status        = request.GET.get('status', '')
    priority      = request.GET.get('priority', '')
    sort_by       = request.GET.get('sort', '-created_at')

    projects = Project.objects.filter(is_active=True).select_related('category')

    if search:
        projects = projects.filter(
            Q(title_ar__icontains=search)       | Q(title_en__icontains=search) |
            Q(description_ar__icontains=search) | Q(description_en__icontains=search) |
            Q(keywords_ar__icontains=search)    | Q(keywords_en__icontains=search) |
            Q(location_ar__icontains=search)    | Q(location_en__icontains=search)
        )
    if category_slug: projects = projects.filter(category__slug=category_slug)
    if status:        projects = projects.filter(status=status)
    if priority:      projects = projects.filter(priority=priority)

    sort_options = {
        'newest':      '-created_at',
        'oldest':      'created_at',
        'most_viewed': '-views_count',
        'most_liked':  '-likes_count',
        'alphabetical':'title_ar',
        'priority':    '-priority',
        'progress':    '-raised_amount',
    }
    projects = projects.order_by(sort_options.get(sort_by, '-created_at'))

    paginator = Paginator(projects, 12)
    page_obj  = paginator.get_page(request.GET.get('page'))

    categories = ProjectCategory.objects.filter(is_active=True).annotate(
        projects_count=Count('projects', filter=Q(projects__is_active=True))
    ).order_by('order')

    # ── إحصائيات (query واحدة + cache) ──
    proj_stats = cache.get('all_projects_stats')
    if not proj_stats:
        proj_stats = Project.objects.filter(is_active=True).aggregate(
            total=Count('id'),
            featured=Count('id', filter=Q(is_featured=True)),
            completed=Count('id', filter=Q(status='completed')),
        )
        cache.set('all_projects_stats', proj_stats, 60 * 5)

    context = {
        'projects':           page_obj,
        'categories':         categories,
        'search':             search,
        'current_category':   category_slug,
        'current_status':     status,
        'current_priority':   priority,
        'current_sort':       sort_by,
        'total_projects':     proj_stats['total'],
        'featured_projects':  proj_stats['featured'],
        'completed_projects': proj_stats['completed'],
        'page_title':         _('جميع المشاريع'),
        'meta_description':   _('تصفح جميع مشاريع جمعية نسائم فلسطين الخيرية'),
    }
    return render(request, 'projects/all_projects.html', context)


def category_projects(request, slug):
    """صفحة مشاريع فئة معينة"""
    category = get_object_or_404(ProjectCategory, slug=slug, is_active=True)
    search   = request.GET.get('q', '').strip()
    status   = request.GET.get('status', '')
    sort_by  = request.GET.get('sort', '-created_at')

    projects = category.projects.filter(is_active=True).select_related('category')

    if search:
        projects = projects.filter(
            Q(title_ar__icontains=search)       | Q(title_en__icontains=search) |
            Q(description_ar__icontains=search) | Q(description_en__icontains=search) |
            Q(keywords_ar__icontains=search)    | Q(keywords_en__icontains=search)
        )
    if status: projects = projects.filter(status=status)

    sort_options = {
        'newest':      '-created_at',
        'oldest':      'created_at',
        'most_viewed': '-views_count',
        'alphabetical':'title_ar',
    }
    projects = projects.order_by(sort_options.get(sort_by, '-created_at'))

    paginator = Paginator(projects, 12)
    page_obj  = paginator.get_page(request.GET.get('page'))

    # ── إحصائيات (query واحدة بدل 4) ──
    stats = projects.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        active=Count('id',    filter=Q(status='active')),
        planning=Count('id',  filter=Q(status='planning')),
    )

    context = {
        'category':     category,
        'projects':     page_obj,
        'category_stats': {
            'total':     stats['total'],
            'completed': stats['completed'],
            'active':    stats['active'],
            'planning':  stats['planning'],
        },
        'search':          search,
        'current_status':  status,
        'current_sort':    sort_by,
        'page_title':      f'{_("مشاريع")} {category.name_ar}',
        'meta_description': category.description_ar or f'{_("مشاريع فئة")} {category.name_ar}',
    }
    return render(request, 'projects/category_projects.html', context)


def search_projects(request):
    """البحث المتقدم في المشاريع"""
    query       = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    status      = request.GET.get('status', '')
    priority    = request.GET.get('priority', '')
    sort_by     = request.GET.get('sort', '-created_at')

    projects = Project.objects.filter(is_active=True).select_related('category')

    if query:
        projects = projects.filter(
            Q(title_ar__icontains=query)        | Q(title_en__icontains=query) |
            Q(summary_ar__icontains=query)      | Q(summary_en__icontains=query) |
            Q(description_ar__icontains=query)  | Q(description_en__icontains=query) |
            Q(keywords_ar__icontains=query)     | Q(keywords_en__icontains=query) |
            Q(location_ar__icontains=query)     | Q(location_en__icontains=query) |
            Q(category__name_ar__icontains=query) | Q(category__name_en__icontains=query)
        )

    if category_id:
        try: projects = projects.filter(category_id=int(category_id))
        except (ValueError, TypeError): pass
    if status:   projects = projects.filter(status=status)
    if priority: projects = projects.filter(priority=priority)

    sort_mapping = {
        '-created_at': '-created_at', 'created_at': 'created_at',
        '-views_count': '-views_count', '-likes_count': '-likes_count',
        'title_ar': 'title_ar', 'title_en': 'title_en',
        'relevance': ('-is_featured', '-views_count', '-created_at'),
    }
    order = sort_mapping.get(sort_by, '-created_at')
    projects = projects.order_by(*order) if isinstance(order, tuple) else projects.order_by(order)

    # الكلمات المفتاحية الشائعة
    popular_keywords = cache.get('popular_keywords')
    if not popular_keywords:
        popular_keywords = []
        for project in Project.objects.filter(is_active=True).only('keywords_ar', 'keywords_en')[:20]:
            for field in (project.keywords_ar, project.keywords_en):
                if field:
                    popular_keywords.extend([k.strip() for k in field.split(',') if k.strip()][:2])
        popular_keywords = list(dict.fromkeys(popular_keywords))[:8]
        cache.set('popular_keywords', popular_keywords, 60 * 60 * 24)

    popular_searches = [
        _('تعليم'), _('صحة'), _('إغاثة'), _('كفالة'),
        _('بناء'), _('أيتام'), _('طوارئ'), _('ماء'),
    ]

    all_quick_searches = list(dict.fromkeys(popular_keywords + popular_searches))[:10]

    paginator = Paginator(projects, 12)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    context = {
        'projects':         page_obj,
        'page_obj':         page_obj,
        'query':            query,
        'search_query':     query,
        'category':         category_id,
        'selected_category': category_id,
        'status':           status,
        'selected_status':  status,
        'priority':         priority,
        'sort':             sort_by,
        'selected_sort':    sort_by,
        'categories':       ProjectCategory.objects.filter(is_active=True).order_by('order'),
        'popular_keywords': all_quick_searches,
        'popular_searches': popular_searches,
        'total_results':    paginator.count,
        'has_filters':      bool(category_id or status or priority),
        'page_title':       _('نتائج البحث'),
        'meta_description': _('نتائج البحث في مشاريع الجمعية'),
    }
    return render(request, 'projects/search_projects.html', context)


def project_like(request, project_id):
    """إعجاب/إلغاء إعجاب بالمشروع"""
    if request.method != 'POST':
        return JsonResponse({'error': _('طريقة غير مسموحة')}, status=405)

    project  = get_object_or_404(Project, id=project_id, is_active=True)
    user_ip  = get_client_ip(request)

    try:
        like, created = ProjectLike.objects.get_or_create(
            project=project, ip_address=user_ip,
            defaults={'user_agent': request.META.get('HTTP_USER_AGENT', '')}
        )
        if not created:
            like.delete()
            project.likes_count = max(0, project.likes_count - 1)
            liked = False
        else:
            project.likes_count += 1
            liked = True
        project.save(update_fields=['likes_count'])
        return JsonResponse({'success': True, 'liked': liked, 'likes_count': project.likes_count})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def download_document(request, document_id):
    """تحميل مستند المشروع"""
    document = get_object_or_404(ProjectDocument, id=document_id, is_active=True, is_public=True)
    document.increment_download()
    response = HttpResponse(document.file.read(), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{document.file.name.split("/")[-1]}"'
    return response


def increment_project_share(request, project_id):
    """زيادة عدد المشاركات"""
    if request.method != 'POST':
        return JsonResponse({'error': _('طريقة غير مسموحة')}, status=405)
    project = get_object_or_404(Project, id=project_id, is_active=True)
    project.shares_count += 1
    project.save(update_fields=['shares_count'])
    return JsonResponse({'success': True, 'shares_count': project.shares_count})


# ==================== Ajax Views ====================

def get_project_stats(request, project_id):
    project = get_object_or_404(Project, id=project_id, is_active=True)
    return JsonResponse({
        'views':                   project.views_count,
        'likes':                   project.likes_count,
        'shares':                  project.shares_count,
        'progress':                project.get_progress_percentage(),
        'beneficiaries_progress':  project.get_beneficiaries_percentage(),
    })


def get_category_projects_ajax(request, category_id):
    category = get_object_or_404(ProjectCategory, id=category_id, is_active=True)
    limit    = int(request.GET.get('limit', 6))
    projects = category.projects.filter(is_active=True).select_related('category').order_by('-created_at')[:limit]

    data = [{
        'id':       p.id,
        'title':    p.title_ar,
        'summary':  p.summary_ar,
        'image':    p.main_image.url if p.main_image else '',
        'url':      p.get_absolute_url(),
        'status':   p.status,
        'progress': p.get_progress_percentage(),
        'likes':    p.likes_count,
        'views':    p.views_count,
    } for p in projects]

    return JsonResponse({'projects': data})


# ==================== Class-Based Views ====================

class ProjectListView(ListView):
    model               = Project
    template_name       = 'projects/all_projects.html'
    context_object_name = 'projects'
    paginate_by         = 12

    def get_queryset(self):
        return Project.objects.filter(is_active=True).select_related('category').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ProjectCategory.objects.filter(is_active=True).order_by('order')
        context['page_title'] = _('جميع المشاريع')
        return context


class ProjectDetailView(DetailView):
    model               = Project
    template_name       = 'projects/project_detail.html'
    context_object_name = 'project'
    slug_field          = 'slug'

    def get_queryset(self):
        return Project.objects.filter(is_active=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object

        if not self.request.session.get(f'viewed_project_{project.id}'):
            project.increment_views()
            self.request.session[f'viewed_project_{project.id}'] = True

        user_ip = get_client_ip(self.request)
        context.update({
            'images':           project.images.filter(is_active=True).order_by('order'),
            'videos':           project.videos.filter(is_active=True).order_by('order'),
            'documents':        project.documents.filter(is_active=True, is_public=True),
            'related_projects': Project.objects.filter(
                category=project.category, is_active=True
            ).exclude(id=project.id).select_related('category').order_by('-views_count')[:6],
            'user_liked': ProjectLike.objects.filter(project=project, ip_address=user_ip).exists(),
        })
        return context


# ==================== API Endpoints ====================

def _project_to_dict(project, request=None):
    d = {
        'id':          project.id,
        'title_ar':    project.title_ar,
        'title_en':    project.title_en,
        'summary_ar':  project.summary_ar,
        'image':       project.main_image.url if project.main_image else None,
        'status':      project.status,
        'progress':    project.get_progress_percentage(),
        'views_count': project.views_count,
        'likes_count': project.likes_count,
        'created_at':  project.created_at.isoformat(),
    }
    if hasattr(project, 'category') and project.category:
        d['category'] = {'id': project.category.id, 'name_ar': project.category.name_ar}
    if request:
        d['url'] = request.build_absolute_uri(project.get_absolute_url())
    return d


def get_featured_projects_api(request):
    return JsonResponse({'featured_projects': [_project_to_dict(p, request) for p in get_featured_projects()]})

def get_recent_projects_api(request):
    limit = int(request.GET.get('limit', 10))
    return JsonResponse({'recent_projects': [_project_to_dict(p, request) for p in get_recent_projects(limit)]})

def get_popular_projects_api(request):
    limit = int(request.GET.get('limit', 10))
    return JsonResponse({'popular_projects': [_project_to_dict(p, request) for p in get_popular_projects(limit)]})

def get_project_statistics_api(request):
    return JsonResponse({'statistics': get_project_statistics()})

def get_categories_api(request):
    categories = ProjectCategory.objects.filter(is_active=True).order_by('order')
    data = [{
        'id':          c.id,
        'name_ar':     c.name_ar,
        'name_en':     c.name_en,
        'slug':        c.slug,
        'icon':        c.icon,
        'color':       c.color,
        'projects_count': c.get_projects_count(),
        'image':       c.image.url if c.image else None,
    } for c in categories]
    return JsonResponse({'categories': data})


# ==================== صفحة المشروع غير موجود ====================

def project_not_found_page(request):
    return render(request, 'projects/project_not_found.html', {
        'page_title':       _('المشروع غير موجود'),
        'meta_description': _('المشروع الذي تبحث عنه غير موجود أو تم حذفه'),
    })

def project_not_found(request, exception):
    return render(request, 'projects/project_not_found.html', {
        'page_title':       _('المشروع غير موجود'),
        'meta_description': _('المشروع الذي تبحث عنه غير موجود أو تم حذفه'),
    }, status=404)