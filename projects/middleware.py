
from django.shortcuts import redirect
from django.urls import reverse


class ProjectNotFoundMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # If 404 and URL starts with /projects/
        if response.status_code == 404 and request.path.startswith('/projects/project/'):
            return redirect('projects:project_not_found')

        return response


