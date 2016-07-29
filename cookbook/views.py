from django.shortcuts import render
from .services import get_recipes_with_cache as get_recipes


def recipes_view(request):
    return render(request, 'cookbook/recipes.html', {
        'recipes': get_recipes()
    })
