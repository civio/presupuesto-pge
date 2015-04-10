# -*- coding: UTF-8 -*-

from budget_app.models import *
from budget_app.loaders.budget_loader import BudgetLoader
from collections import namedtuple
import csv
import os.path


class PGEBudgetLoader(BudgetLoader):
    ItemId = namedtuple('ItemId', 'ec_code fc_code ic_code fdc_code item_number')

    # We don't have funding categories, so create a dummy one and assign everything to it
    def get_default_funding_categories(self):
        categories = BudgetLoader.get_default_funding_categories(self)
        categories.append({ 
                        'expense': True, 
                        'source': 'X',
                        'fund_class': 'XX',
                        'fund': 'XXX',
                        'description': 'Gastos'
                    })
        categories.append({ 
                        'expense': False, 
                        'source': 'X',
                        'fund_class': 'XX',
                        'fund': 'XXX',
                        'description': 'Ingresos'
                    })
        return categories

    # Add a dummy chapter 6 article for some odd Social Security expenses (see note below)
    def get_default_economic_categories(self):
        categories = BudgetLoader.get_default_economic_categories(self)
        categories.append({
                        'expense': True,
                        'chapter': '6',
                        'article': '69',
                        'description': 'Inversiones reales'
                    })
        return categories

    # Get all the relevant bits from an input line, and put them all into a dictionary
    def add_data_item(self, items, line, is_expense, is_actual):
        # Get the amount. For execution data, pick "Obligaciones/Créditos reconocidas/os"
        if is_actual:
            amount = line[10 if is_expense else 9]
        else:
            amount = line[7]

        # We treat the functional code a bit differently, we pass it on split into its
        # elements, while we pass other codes in one chunk. The only reason is that some
        # child loaders needed to do some manipulation and it's cleaner to override this
        # function, and not the actual loading. We could treat other categories in the same way.
        if is_expense:
            fc_area = line[2][0:1]
            fc_policy = line[2][0:2]
            fc_function = line[2][0:3]
            fc_programme = line[2]
        else:
            # Income data is often not classified functionally, so we use the fake category we 
            # created before.
            fc_area = 'X'
            fc_policy = 'XX'
            fc_function = 'XXX'
            fc_programme = 'XXXX'

        # Ignore internal transfers between the central administration and its dependent 
        # children. We take care of the expense side here, but income is done in 
        # process_data_items, see below.
        if fc_programme == '000X':
            return

        # Because of the way headings work in the PGE (their descriptions are not consistent),
        # we need to do some ugly stuff, tagging headings with the entity id. But we've managed
        # to make that transparent to the loading process.
        ec_code = line[3]
        ec_chapter = ec_code[0]
        ec_article = ec_code[0:2] if len(ec_code) >= 2 else None
        ec_heading = ec_code if len(ec_code) >= 3 else None
        ec_subheading = None

        # Gather all the relevant bits and store them to be processed
        items.append({
                'ic_code': line[1],
                'fc_area': fc_area,
                'fc_policy': fc_policy,
                'fc_function': fc_function,
                'fc_programme': fc_programme,
                'ec_chapter': ec_chapter,
                'ec_article': ec_article,
                'ec_heading': ec_heading,
                'ec_subheading': ec_subheading,
                'ec_code': line[3], # Redundant, but convenient
                'fdc_code': 'XXX',  # Not used for these budgets
                'item_number': line[5],
                'description': self._escape_unicode(line[6]),
                'amount': self._read_spanish_number(amount)
            })

    # We need to do a couple of hacks to work around the PGE data structure, before we call
    # the base class to do the actual processing
    def process_data_items(self, budget, items, is_expense, is_actual):
        def _substract_from_parent(items_dictionary, parent_id, amount):
            parent_amount = items_dictionary[parent_id]['amount']
            items_dictionary[parent_id]['amount'] = parent_amount - amount

        # First, convert the incoming list into a dictionary
        items_dictionary = {}
        for item in items:
            uid = PGEBudgetLoader.ItemId( item['ec_code'], 
                                        item['fc_programme'], 
                                        item['ic_code'], 
                                        item['fdc_code'],
                                        item['item_number'])
            items_dictionary[uid] = item

        # Avoid double counting the subtotals: for each item we substract its amount from
        # its parent category. Note this relies on moving through the tree downwards, hence
        # the need to sort the list (by x[0] -the economic code- and x[4] -the item number-)
        for uid in sorted(items_dictionary.keys(), key=lambda x: [x[0],x[4]]):
            item = items_dictionary[uid]
            if item['item_number']:     # We have an item, substract from its category
                parent_id = PGEBudgetLoader.ItemId( item['ec_code'],
                                                    item['fc_programme'], 
                                                    item['ic_code'], 
                                                    item['fdc_code'],
                                                    '')
                _substract_from_parent(items_dictionary, parent_id, item['amount'])

            else:                       # We have a category, substract from its parent
                code_length = len(item['ec_code'])
                if code_length > 1:
                    parent_code_length = min(2, code_length-1)
                    parent_id = PGEBudgetLoader.ItemId( item['ec_code'][0:parent_code_length],
                                                        item['fc_programme'], 
                                                        item['ic_code'], 
                                                        item['fdc_code'],
                                                        '')
                    _substract_from_parent(items_dictionary, parent_id, item['amount'])

        # Remove items with zero amount, i.e. subtotals, they have no use
        for uid in items_dictionary.keys():
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
            if is_expense and item['ec_chapter']=='6' and item['ec_article']==None:
                item['ec_article']='69'
                item['ec_code']='69'

            # We want to get rid of internal transfers. We did the expense side above,
            # in add_data_item, but we couldn't remove the income side there, because we
            # would then have an invalid subtotal at the chapter level, and the final sum
            # would still include the internal transfers. So we remove them here. :/
            if not is_expense:
                if item['ec_article'] and item['ec_article'] in ['40', '41', '42', '43', '70', '71', '72', '73']:
                    items_dictionary.pop(uid)

        # Continue the normal processing for the remaining items
        BudgetLoader.process_data_items(self, budget, items_dictionary.values(), is_expense, is_actual)

    def _escape_unicode(self, s):
        return s.decode('utf-8')
