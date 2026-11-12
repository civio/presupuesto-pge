# -*- coding: UTF-8 -*-

from budget_app.models import *
from budget_app.loaders import SimpleBudgetLoader
from collections import namedtuple


class PGEBudgetLoader(SimpleBudgetLoader):
    # Identifies a line, or the subtotal it belongs to, within the data files
    ItemId = namedtuple('ItemId', 'is_expense is_actual ec_code fc_code ic_code item_number')

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
        _, code, short_description, long_description = line
        return {
            'institution': code[0:2],
            'section': code[0:4] if len(code) > 2 else None,
            'department': code if len(code) > 4 else None,
            'description': long_description or short_description
        }

    # Unlike in other sites, each column has the whole code, not just its last digits
    def parse_economic_category(self, line):
        _, income_or_expense, chapter, article, heading, subheading, _, description = line
        return {
            'expense': income_or_expense.upper() == 'G',
            'chapter': chapter or None,
            'article': article or None,
            'heading': heading or None,
            'subheading': subheading or None,
            'description': description
        }

    def parse_functional_category(self, line):
        year, area, policy, function, programme, _, description = line
        return {
            'area': area,
            'policy': policy or None,
            'function': function or None,
            'programme': self._map_programme(year, programme) if programme else None,
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
    # some are tagged with the managing centre, like '420/07001'. So the heading is the
    # whole code, not its first three digits.
    def _split_economic_code(self, ec_code):
        chapter, article, _, _ = super()._split_economic_code(ec_code)
        return chapter, article, (ec_code if len(ec_code) >= 3 else None), None

    def parse_item(self, filename, line):
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
    # need to do a couple of hacks before the lines are saved
    def load_budget_items(self, budget, budget_items):
        super().load_budget_items(budget, self._remove_subtotals([item for item in budget_items if item]))

    def _remove_subtotals(self, items):
        def _substract_from_parent(items_dictionary, parent_id, amount):
            parent_amount = items_dictionary[parent_id]['amount']
            items_dictionary[parent_id]['amount'] = parent_amount - amount

        # First, convert the incoming list into a dictionary. The keys include whether each line
        # is income or expense, budget or execution, so a line only finds its parent in its own file.
        items_dictionary = {}
        for item in items:
            uid = PGEBudgetLoader.ItemId(item['is_expense'],
                                         item['is_actual'],
                                         item['ec_code'],
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
                parent_id = uid._replace(item_number='')
                _substract_from_parent(items_dictionary, parent_id, item['amount'])

            else:                       # We have a category, substract from its parent
                code_length = len(item['ec_code'])
                if code_length > 1:
                    parent_code_length = min(2, code_length-1)
                    parent_id = uid._replace(ec_code=item['ec_code'][0:parent_code_length], item_number='')
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
            if item['is_expense'] and item['ec_code'] == '6':
                item['ec_code'] = '69'

            # We want to get rid of internal transfers. We did the expense side above,
            # in parse_item, but we couldn't remove the income side there, because we
            # would then have an invalid subtotal at the chapter level, and the final sum
            # would still include the internal transfers. So we remove them here. :/
            if not item['is_expense']:
                if len(item['ec_code']) >= 2 and item['ec_code'][0:2] in ['40', '41', '42', '43', '70', '71', '72', '73']:
                    items_dictionary.pop(uid)

        return list(items_dictionary.values())

    def _get_delimiter(self):
        return ';'
