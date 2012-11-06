# -*- coding: utf-8 -*-
try:
    from pyxmli import CURRENCIES
except ImportError:
    CURRENCIES = []


class Address(object):
    '''
    Represents a postal address.
    '''
    def __init__(self, address_dict={}, mutable=False):
        '''
        Initializes a new instance of the Address class.
        @param address_dict:dict Address dictionary.
        '''
        self.__address_dict = address_dict
        self.__mutable = mutable
        
    @property
    def street_address(self):    
        return ('%s %s' % (self.number, self.street)).strip(' ')

    def __getattr__(self, field):
        '''
        Gets a field of the address.
        @param field:str Field name.
        @return: str
        '''
        #FIXME: Temporary workaround
        if field == 'street_address':
            field = 'street'
        try:
            return self.__address_dict[field]
        except KeyError:
            raise AttributeError, field

    def __setattribute__(self, field, value):
        '''
        Sets an address field.
        @param field:str Field name.
        @param value:str Field value.
        '''
        if not self.__mutable:
            raise Exception("Address is not mutable.")

        if field not in ["street_address", "city", "zipcode", "state",
                         "country"]:
            raise AttributeError("Address has no such attribute.")

        self.__address_dict[field] = value


class CurrencyMetrics(object):
    '''
    Represents a set of data digested for a specific currency
    '''
    def __init__(self, currency_code, data):
        '''
        Initializes a new instance of the CurrencyMetrics class.
        @param currency_code:str Currency code.
        @param data: dict Source object. 
        '''
        if len(CURRENCIES) and currency_code not in CURRENCIES:
            raise ValueError('Unsupported currency ' + currency_code)

        if not data or not len(data):
            raise ValueError('Invalid data source object')

        self.__currency_code = currency_code
        self.__data = data

    @property
    def currency(self):
        '''
        Gets the currency in which the current metrics are labeled.
        @return: str
        '''
        return self.__currency_codes

    @property
    def min(self):
        '''
        Gets the smallest invoice paid in the current currency
        @return: float
        '''
        return self.__data['min']

    @property
    def max(self):
        '''
        Gets the largest invoice paid in the current currency
        @return: float
        '''
        return self.__data['max']

    @property
    def average(self):
        '''
        Gets the average invoice amount paid in the current currency
        @return: float
        '''
        return self.__data['average']

    @property
    def sum(self):
        '''
        Gets the total revenue recorded in the current currency
        @return: float
        '''
        return self.__data['sum']

    @property
    def total_taxes(self):
        '''
        Gets the total amount of taxes.
        @return: float
        '''
        return self.__data['totalTaxes']

    @property
    def total_discounts(self):
        '''
        Gets the total amount of discounts.
        @return: float
        '''
        return self.__data['totalDiscounts']

    @property
    def invoices_count(self):
        '''
        Gets the total number of invoices exchanged in the current currency
        @return: int
        '''
        return self.__data['invoicesCount']

    @property
    def items(self):
        '''
        Gets the smallest invoice paid in the current currency
        @return: float
        '''
        return self.__data['items']

    @property
    def taxes(self):
        '''
        Gets the taxes recorded in the currency taxes
        @return: list
        '''
        return [Treatment(i) for i in self.__data['taxes']]

    @property
    def discounts(self):
        '''
        Gets the discounts recorded in the currency taxes
        @return: list
        '''
        return [Treatment(i) for i in self.__data['discounts']]


class Treatment(object):
    '''
    Represents an invoice line discount or tax.
    '''
    def __init__(self, data):
        '''
        Initializes a new instance of the Treatment class.
        @param data: dict Source datas
        '''
        self.__data = data

    @property
    def type(self):
        '''
        Gets the type of the treatment.
        @return: str
        '''
        return self.__data['type']

    @property
    def value(self):
        '''
        Gets the value of the tax or the discount.
        @return: float
        '''
        return self.__data['value']

    @property
    def name(self):
        '''
        Gets the name of the tax or discount.
        @return: str
        '''
        return self.__data['name']
