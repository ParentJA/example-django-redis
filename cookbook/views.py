from django.shortcuts import render
from django.views.decorators.cache import cache_page
from .services import get_recipes_without_cache as get_recipes

# Cache time to live is 15 minutes.
CACHE_TTL = 60 * 15


@cache_page(CACHE_TTL)
def recipes_view(request):
    return render(request, 'cookbook/recipes.html', {
        'recipes': get_recipes()
    })
