from django.core.cache import cache
from django.db import reset_queries, connection
from .models import Recipe


def get_recipes_without_cache():
    # Reset database queries.
    reset_queries()

    # Retrieve recipes.
    recipes = list(Recipe.objects.prefetch_related('ingredients'))

    # Count database queries.
    print 'Database called {count} times.'.format(count=len(connection.queries))

    return recipes


def get_recipes_with_cache():
    # Reset database queries.
    reset_queries()

    # Retrieve recipes.
    if 'recipes' in cache:
        recipes = cache.get('recipes')
    else:
        recipes = list(Recipe.objects.prefetch_related('ingredients'))
        cache.set('recipes', recipes)

    # Count database queries.
    print 'Database called {count} times.'.format(count=len(connection.queries))

    return recipes
