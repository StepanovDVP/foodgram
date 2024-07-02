import json

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    """Добавить все ингредиенты в базу данных."""

    help = 'Load ingredients from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str,
                            help='The file path of the JSON file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            for item in data:
                Ingredient.objects.create(
                    name=item['name'],
                    measurement_unit=item['measurement_unit'])
        self.stdout.write(
            self.style.SUCCESS('Data successfully loaded'))
