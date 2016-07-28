from django.db import models


class Recipe(models.Model):
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name


class Food(models.Model):
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name


class Ingredient(models.Model):
    recipe = models.ForeignKey(Recipe)
    food = models.ForeignKey(Food)

    # ex. 1/8 = 0.125, 1/4 = 0.250
    amount = models.DecimalField(max_digits=6, decimal_places=3)

    # ex. tsp, tbsp, cup
    unit_of_measure = models.CharField(max_length=255)

    def __unicode__(self):
        return '{recipe}: {amount} {unit_of_measure} {food}'.format(
            recipe=self.recipe,
            amount=self.amount,
            unit_of_measure=self.unit_of_measure,
            food=self.food
        )
