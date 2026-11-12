# -*- coding: UTF-8 -*-

from budget_app.models import *
from budget_app.loaders import SimpleBudgetLoader
from collections import namedtuple


class PGEBudgetLoader(SimpleBudgetLoader):
    ItemId = namedtuple('ItemId', 'ec_code fc_code ic_code item_number')

    # The 2023 budget renamed some programmes, God knows why. We keep their old codes,
    # both in the data and in the classification, so the time series stays intact.
    PROGRAMME_MAPPING_2023 = {
        '211A': '211M',   # Pensiones contributivas de la Seguridad Social
        '211B': '211N',   # Pensiones de Clases Pasivas
        '211C': '211O',   # Otras pensiones y prestaciones de Clases Pasivas
        '212A': '212M',   # Pensiones no contributivas y prestaciones asistenciales
        '212C': '212O',   # Complementos por mínimos de las pensiones contributivas
        '221B': '221M',   # Subsidios de incapacidad temporal y otras prestaciones económicas de la Seguridad Social
        '223A': '223M',   # Prestaciones de garantía salarial
        '224A': '224M',   # Prestaciones económicas por cese de actividad
    }

    def _map_programme(self, year, programme):
        if year == '2023':
            return self.PROGRAMME_MAPPING_2023.get(programme, programme)
        return programme

    # The classifications change every year, so there's one in each year's folder, in the
    # format scraper-pge writes, with a header and the year in the first column
    def parse_institutional_category(self, line):
        if line[0] == 'EJERCICIO':
            return None

        # Prefer the long description if it exists, otherwise the short one
        return {
            'institution': line[1][0:2],
            'section': (line[1][0:4] if len(line[1]) > 2 else None),
            'department': (line[1] if len(line[1]) > 4 else None),
            'description': line[2] if len(line)<=3 or line[3] == "" else line[3]
        }

    # Unlike in other sites, each column has the whole code, not just its last digits
    def parse_economic_category(self, line):
        if line[0] == 'EJERCICIO':
            return None

        return {
            'expense': (line[1].upper() == 'G'),
            'chapter': (line[2] if line[2] != "" else None),
            'article': (line[3] if line[3] != "" else None),
            'heading': (line[4] if line[4] != "" else None),
            'subheading': (line[5] if line[5] != "" else None),
            'description': line[7]
        }

    def parse_functional_category(self, line):
        if line[0] == 'EJERCICIO':
            return None

        description = line[6]

        # If we're not using subprogrammes, insert an empty column where they would go.
        if not self._use_subprogrammes():
            line.insert(5, "")

        return {
            'area': line[1],
            'policy': (line[2] if line[2] != "" else None),
            'function': (line[3] if line[3] != "" else None),
            'programme': (self._map_programme(line[0], line[4]) if line[4] != "" else None),
            'subprogramme': (line[5] if line[5] != "" else None),
            'description': description
        }

    # Add a dummy chapter 6 article for some odd Social Security expenses (see note below).
    # It goes before the ones in the file, which sometimes have their own article 69, so the
    # lookups find it first.
    def load_economic_classification(self, path, budget):
        EconomicCategory(budget=budget,
                         expense=True,
                         chapter='6',
                         article='69',
                         description='Inversiones reales').save()
        super().load_economic_classification(path, budget)

    # Because of the way headings work in the PGE (their descriptions are not consistent),
    # some are tagged with the managing centre, like '420/07001'. So we match the whole code
    # as the heading, instead of its first three digits.
    def fetch_economic_category(self, budget, is_expense, ec_code):
        key = (budget, is_expense, ec_code)
        if key not in self.economic_category_cache:
            ec = EconomicCategory.objects.filter(expense=is_expense,
                                                chapter=ec_code[0],
                                                article=ec_code[0:2] if len(ec_code) >= 2 else None,
                                                heading=ec_code if len(ec_code) >= 3 else None,
                                                subheading=None,
                                                budget=budget)
            self.economic_category_cache[key] = ec.first() if ec else None
        return self.economic_category_cache[key]

    def parse_item(self, filename, line):
        if line[0] == 'EJERCICIO':
            return None

        is_expense = (filename.find('gastos.csv') != -1)
        is_actual = (filename.find('/ejecucion_') != -1)

        # Add a null column for income data, so all the indexes below remain constant
        if not is_expense:
            line.insert(2, None)

        # Get the amount. For execution data, pick "Obligaciones/Créditos reconocidas/os"
        if is_actual:
            amount = line[10 if is_expense else 9]
        else:
            amount = line[7]

        if is_expense:
            fc_code = line[2]

            fc_code = self._map_programme(line[0], fc_code)

            # Ignore internal transfers between the central administration and its dependent
            # children. We take care of the expense side here, but income is done in
            # _remove_subtotals, see below.
            if fc_code == '000X':
                return None
        else:
            fc_code = None

        return {
            'is_expense': is_expense,
            'is_actual': is_actual,
            'ic_code': line[1],
            'ic_institution': line[1][0:2],
            'ic_section': line[1][0:4],
            'ic_department': line[1],
            'fc_code': fc_code,
            'ec_code': line[3],
            'item_number': line[5],
            'description': line[6][0:512],    # The longest ones don't fit in the database
            'amount': self._read_spanish_number(amount)
        }

    # The data files include subtotals for each level of the economic classification, so we
    # need to do a couple of hacks before the lines are saved, one file at a time
    def load_budget_items(self, budget, budget_items):
        items = [item for item in budget_items if item]
        processed_items = []
        for is_expense in [True, False]:
            for is_actual in [False, True]:
                processed_items.extend(self._remove_subtotals(
                    [item for item in items if item['is_expense'] == is_expense and item['is_actual'] == is_actual],
                    is_expense))
        super().load_budget_items(budget, processed_items)

    def _remove_subtotals(self, items, is_expense):
        def _substract_from_parent(items_dictionary, parent_id, amount):
            parent_amount = items_dictionary[parent_id]['amount']
            items_dictionary[parent_id]['amount'] = parent_amount - amount

        # First, convert the incoming list into a dictionary
        items_dictionary = {}
        for item in items:
            uid = PGEBudgetLoader.ItemId(item['ec_code'],
                                         item['fc_code'],
                                         item['ic_code'],
                                         item['item_number'])
            items_dictionary[uid] = item

        # Avoid double counting the subtotals: for each item we substract its amount from
        # its parent category. Note this relies on moving through the tree downwards, hence
        # the need to sort the list (by economic code and item number)
        for uid in sorted(items_dictionary.keys(), key=lambda x: [x.ec_code, x.item_number]):
            item = items_dictionary[uid]
            if item['item_number']:     # We have an item, substract from its category
                parent_id = PGEBudgetLoader.ItemId(item['ec_code'],
                                                   item['fc_code'],
                                                   item['ic_code'],
                                                   '')
                _substract_from_parent(items_dictionary, parent_id, item['amount'])

            else:                       # We have a category, substract from its parent
                code_length = len(item['ec_code'])
                if code_length > 1:
                    parent_code_length = min(2, code_length-1)
                    parent_id = PGEBudgetLoader.ItemId(item['ec_code'][0:parent_code_length],
                                                       item['fc_code'],
                                                       item['ic_code'],
                                                       '')
                    _substract_from_parent(items_dictionary, parent_id, item['amount'])

        # Remove items with zero amount, i.e. subtotals, they have no use
        for uid in list(items_dictionary.keys()):
            item = items_dictionary[uid]
            if item['amount'] == 0:
                items_dictionary.pop(uid)
                continue

            # Some Chapter 6 items are not broken down into articles (see ProgrammeBreakdown
            # notes in the PGE parser). That means they don't show up in the main PGE economic
            # breakdown page -although the final sum is correct-. I create a dummy item here
            # to work around that, i.e. making sure all expense is broken down at least to
            # the article level, for consistency and to make my life easier. (I don't want
            # to be forced to break the budget starting at chapter level just because of this.)
            if is_expense and item['ec_code'] == '6':
                item['ec_code'] = '69'

            # We want to get rid of internal transfers. We did the expense side above,
            # in parse_item, but we couldn't remove the income side there, because we
            # would then have an invalid subtotal at the chapter level, and the final sum
            # would still include the internal transfers. So we remove them here. :/
            if not is_expense:
                if len(item['ec_code']) >= 2 and item['ec_code'][0:2] in ['40', '41', '42', '43', '70', '71', '72', '73']:
                    items_dictionary.pop(uid)

        return list(items_dictionary.values())

    def _get_delimiter(self):
        return ';'
