from django.core.cache import cache
from .models import Recipe


def get_recipes():
    if 'recipes' in cache:
        recipes = cache.get('recipes')
    else:
        recipes = list(Recipe.objects.prefetch_related('ingredient_set__food'))
        cache.set('recipes', recipes)

    return recipes

