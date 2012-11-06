# -*- coding: utf-8 -*-
import re
import hashlib
import httplib
from datetime import date
from greendizer.clients.http import API_ROOT, USER_AGENT
from greendizer.clients.helpers import CurrencyMetrics, Address
from greendizer.clients.base import extract_id_from_uri, timestamp_to_datetime
from greendizer.clients.dal import Resource, Node
from greendizer.clients.http import Request
try:
    from pyxmli import CURRENCIES
except ImportError:
    CURRENCIES = []


PAYMENT_METHOD_GREENDIZER = 'greendizer'
TRANSACTION_TYPE_PAYMENT = 'payment'
TRANSACTION_TYPE_WITHDRAWAL = 'withdrawal'
TRANSACTION_TYPE_UPLOAD = 'upload'
TRANSACTION_STATUS_FAILED = 'failed'
TRANSACTION_STATUS_PENDING = 'pending'
TRANSACTION_STATUS_CANCELED = 'canceled'
TRANSACTION_STATUS_PROCESSED = 'processed'


class User(Resource):
    '''
    Represents a generic user on Greendizer.
    '''
    def __init__(self, client):
        '''
        Initializes a new instance of the User class.
        '''
        super(User, self).__init__(client, "me")
        self.__company = Employer(self)
        self.__settings = Settings(self)
        self.__balances = Node(client,
                               self.uri + 'balances/',
                               Balance)

    @property
    def balances(self):
        '''
        Gets the balances of the current user.
        @return: Node
        '''
        return self.__balances

    @property
    def settings(self):
        '''
        Gets the settings of this user.
        @return: Settings
        '''
        return self.__settings

    @property
    def company(self):
        '''
        Gets the company of this user.
        @return: Company
        '''
        return self.__company

    @property
    def first_name(self):
        '''
        Gets the first name.
        @return: str
        '''
        return self._get_attribute("firstname")

    @property
    def last_name(self):
        '''
        Gets the last name
        @return: str
        '''
        return self._get_attribute("lastname")

    @property
    def full_name(self):
        '''
        Gets the last name
        @return: str
        '''
        return "%s %s" % (self.first_name, self.last_name)

    @property
    def avatar_url(self):
        '''
        Gets the URL of the user's profile picture
        @return: str
        '''
        return self._get_attribute("avatar")

    @property
    def birthday(self):
        '''
        Gets the birthday
        @return: date
        '''
        return self._get_date_attribute("birthday").date()


class Settings(Resource):
    '''
    Represents generic settings attached a user's account.
    '''
    def __init__(self, user):
        '''
        Initializes a new instance of the Settings class.
        @param client:Client Current client instance.
        '''
        self.__user = user
        super(Settings, self).__init__(user.client)

    @property
    def uri(self):
        '''
        Gets the URI of the resource.
        @return:str
        '''
        return self.__user.uri + "settings/"

    @property
    def language(self):
        '''
        Gets the language of the user.
        @return: str
        '''
        return self._get_attribute("language")

    @property
    def region(self):
        '''
        Gets the region of the user
        @return: str
        '''
        return self._get_attribute("region")

    @property
    def currency(self):
        '''
        Gets the currency
        @return: str
        '''
        return self._get_attribute("currency")


class Company(Resource):
    '''
    Represents a generic company's profile on Greendizer.
    '''
    @property
    def uri(self):
        '''
        Gets the URI of the resource.
        @return: str
        '''
        return "/companies/%s/" + self.id

    @property
    def name(self):
        '''
        Gets the name of the company
        @return: str
        '''
        return self._get_attribute("name")

    @property
    def description(self):
        '''
        Gets the description of the company
        @return: str
        '''
        return self._get_attribute("description")

    @property
    def small_logo_url(self):
        '''
        Gets the URL of a small version of the company's logo.
        @return: str
        '''
        return self._get_attribute("smallLogo")

    @property
    def large_logo_url(self):
        '''
        Gets the URL of a large version of the company's logo.
        @return: str
        '''
        return self._get_attribute("largeLogo")
    
    @property
    def address(self):
        '''
        Gets the company's address.
        @returns: Address
        '''
        return Address(self._get_attribute('address'), mutable=False)
    
    @property
    def legal_mentions(self):
        '''
        Gets the mandatory legal mentions that should be added to every
        invoice sent.
        @returns: str
        '''
        return self._get_attribute('legalMentions')


class Employer(Company):
    '''
    Represents the company employing a user on Greendizer.
    '''
    def __init__(self, user):
        '''
        Initializes a new instance of the Settings class.
        @param user:User currently authenticated user.
        '''
        self.__user = user
        super(Employer, self).__init__(user.client)

    @property
    def uri(self):
        '''
        Gets the URI of the resource.
        @return: str
        '''
        return self.__user.uri + "company/"


class EmailBase(Resource):
    '''
    Represent an email address on Greendizer
    '''
    def __init__(self, user, identifier):
        '''
        Initializes a new instance of the Email class
        @param user:User Current user.
        @param identifier:str ID of the email resource.
        '''
        if "@" in identifier:
            identifier = hashlib.sha1(identifier.lower()).hexdigest()

        super(EmailBase, self).__init__(user.client, identifier)
        self.__user = user

    @property
    def uri(self):
        '''
        Gets the URI of this resource.
        @return: str
        '''
        return "%semails/%s/" % (self.__user.uri, self.id)

    @property
    def label(self):
        '''
        Gets the label of this address
        @return: str
        '''
        return self._get_attribute("label")

    @property
    def user(self):
        '''
        Gets the user to which this email address is attached.
        @return: User
        '''
        return self.__user


class PDFError(Exception):
    pass


class InvoiceBase(Resource):
    '''
    Represent an email address on Greendizer
    '''
    def __init__(self, email, identifier):
        '''
        Initializes a new instance of the Email class
        @param email:Email Email instance of the origin of this invoice.
        @param identifier:str ID of the email resource.
        '''
        super(InvoiceBase, self).__init__(email.client, identifier)
        self.__email = email
        self.__payments = PaymentNode(self)

    @property
    def email(self):
        '''
        Gets the email instance to which this invoice is attached.
        @return:Email
        '''
        return self.__email

    @property
    def uri(self):
        '''
        Gets the URI of this resource.
        @return: str
        '''
        return "%sinvoices/%s/" % (self.__email.uri, self.id)

    @property
    def payments(self):
        '''
        Gets the payments associated with this invoice.
        @return: Node
        '''
        return self.__payments


    @property
    def name(self):
        '''
        Gets the name of the invoice.
        @return: str
        '''
        return self._get_attribute("name")

    @property
    def description(self):
        '''
        Gets the description of the invoice
        @return: str
        '''
        return self._get_attribute("description")

    @property
    def total(self):
        '''
        Gets the total of the invoice.
        @return: float
        '''
        return self._get_attribute("total")

    @property
    def remaining(self):
        '''
        Gets the remaining amount to this invoice.
        @return: float
        '''
        if self.paid:
            return 0.0

        self.payments.all.populate(offset=None, limit=None)
        return float(sum([payment.amount for payment in self.payments.all]))


    @property
    def body(self):
        '''
        Gets the body of the invoice.
        @return: str
        '''
        return self._get_attribute("body")

    @property
    def currency(self):
        '''
        Gets the currency of the invoice.
        @return:str
        '''
        return self._get_attribute("currency")

    @property
    def date(self):
        '''
        Gets the invoice date.
        @return: datetime
        '''
        return self._get_date_attribute("date")

    @property
    def due_date(self):
        '''
        Gets the due date of the invoice.
        @return: datetime
        '''
        return self._get_date_attribute("due_date")

    @property
    def secret_key(self):
        '''
        Gets the secret key of the invoice.
        @return: str
        '''
        return self._get_attribute("secretKey")

    def __get_archived(self):
        '''
        Gets a value indicating whether the invoice has been archived or not.
        @return: bool
        '''
        return self._get_attribute("archived")

    def __set_archived(self, value):
        '''
        Sets a value indicating to mark the invoice as archived or not.
        @param value:bool
        '''
        self._register_update("archived", value)

    def __get_read(self):
        '''
        Gets a value indicating whether the invoice has been read or not.
        @return: bool
        '''
        return self._get_attribute("read")

    def __set_read(self, value):
        '''
        Sets a value indicating whether the invoice has been read or not.
        @param value:bool
        '''
        self._register_update("read", value)

    def __get_flagged(self):
        '''
        Gets a value indicating whether the invoice has been flagged or not.
        @return: bool
        '''
        return self._get_attribute("flagged")

    def __set_flagged(self, value):
        '''
        Sets a value indicating whether the invoice has been flagged or not.
        @param value:bool
        '''
        self._register_update("flagged", value)

    def __get_paid(self):
        '''
        Gets a value indicating whether the invoice has been paid or not.
        @return: bool
        '''
        return self._get_attribute("paid")

    def __set_paid(self, value):
        '''
        Sets a value indicating whether the invoice has been paid or not.
        @param value:bool
        '''
        self._register_update("paid", value)

    archived = property(__get_archived, __set_archived)
    read = property(__get_read, __set_read)
    flagged = property(__get_flagged, __set_flagged)
    paid = property(__get_flagged, __set_flagged)
    
    def get_pdf(self, locale='en'):
        '''
        Gets the URI of the PDF version of the invoice
        @return: str
        '''
        http = httplib.HTTP(API_ROOT)
        http.request('GET', self.uri)
        http.putheader('Accept', 'application/pdf')
        http.putheader('Accept-Language', locale)
        http.putheader('User-Agent', USER_AGENT)
        response = http.getresponse()
        if response.status != 302:
            raise PDFError
        return response.headers['Location'] 

    @classmethod
    def from_uri(cls, user, uri):
        '''
        Instantiates an Invoice class instance using a URI.
        @param user:User instance
        @param uri:str URI
        @return: InvoiceBase
        '''
        if '/me/' in user.uri:
            user.load_info()
            
        match = re.compile('/' + user.uri +
                           'emails\/(?P<email>.+)\/invoices' +
                           '\/(?P<id>.+)\/$',
                           re.LOCALE).search(uri)
        if not match:
            return
        
        return cls(user.emails[match.groupdict()['email']],
                   match.groupdict()['id'])


class InvoiceNodeBase(Node):
    '''
    Represents a node giving access to invoices.
    '''
    def __init__(self, email, resource_cls=InvoiceBase):
        '''
        Initializes a new instance of the InvoiceNode class.
        @param email:Email Email instance to which the node is tied.
        @param resource_cls:Class Class with which invoices will be instantiated
        '''
        self.__email = email
        super(InvoiceNodeBase, self).__init__(email.client,
                                              uri=email.uri + "invoices/",
                                              resource_cls=resource_cls)

    def get(self, identifier, **kwargs):
        '''
        Gets an invoice using its ID.
        @param identifier:str ID of the invoice.
        @return: Invoice
        '''
        return super(InvoiceNodeBase, self).get(self.__email, identifier,
                                                **kwargs)

    @property
    def email(self):
        '''
        Gets the email instance to which this node is attached.
        @return: Email
        '''
        return self.__email

    @property
    def archived(self):
        '''
        Gets a collection to manipulate archived invoices.
        @return: Collection
        '''
        return self.search("location==1")

    @property
    def trashed(self):
        '''
        Gets a collection to manipulate trashed invoices.
        @return: Collection
        '''
        return self.search("location==2")

    @property
    def unread(self):
        '''
        Gets a collection to manipulate unread invoices.
        @return: Collection
        '''
        return self.search("read==0|location<<2")

    @property
    def flagged(self):
        '''
        Gets a collection to manipulate flagged invoices.
        @return: Collection
        '''
        return self.search("flagged==1|location<<2")

    @property
    def due(self):
        '''
        Gets a collection to manipulate all due invoices.
        @return: Collection
        '''
        return self.search("paid==0|location<<2|canceled==0")

    @property
    def overdue(self):
        '''
        Gets a collection to manipulate overdue invoices.
        @return: Collection
        '''
        return self.search("paid==0|location<<2|canceled==0|dueDate>>"
                           + date.today().isoformat())


class Payment(Resource):
    '''
    Represents a payment recorded for an invoice.
    '''
    def __init__(self, invoice, identifier):
        '''
        Initializes a new instance of the Payment class.
        @param invoice:InvoiceBase instance
        @param identifier:str ID
        '''
        self.__invoice = invoice
        super(Payment, self).__init__(invoice.client, identifier)


    @property
    def uri(self):
        '''
        Gets the URI of the payment.
        @return: str
        '''
        return '%spayments/%s' % (self.__invoice.uri, self.id)


    @property
    def invoice(self):
        '''
        Gets the invoice to which the payment is attached.
        @return: InvoiceBase
        '''
        return self.__invoice


    @property
    def currency(self):
        '''
        Gets the currency in which the payment was recorded.
        return: str
        '''
        return self.invoice.currency


    @property
    def date(self):
        '''
        Gets the Date of the payment.
        @return: date
        '''
        return self._get_date_attribute('date')


    @property
    def amount(self):
        '''
        Gets the amount of the payment.
        @return: float
        '''
        return self._get_attribute('amount')


    @property
    def method(self):
        '''
        Gets the payment method.
        @return: str
        '''
        return self._get_attribute('method')


    @property
    def transaction(self):
        '''
        Gets the transaction at the origin of this payment object if any.
        @returns: Transaction
        '''
        if self.method != PAYMENT_METHOD_GREENDIZER:
            return None

        return Transaction.from_uri(self.invoice.client.user,
                                    self._get_attribute('ref'))


class PaymentNode(Node):
    '''
    Represents a node opening access to payments related to an invoice.
    '''
    def __init__(self, invoice):
        '''
        Initializes a new instance of the PaymentNode class.
        @param invoice:InvoiceBase Parent invoice instance.
        '''
        self.__invoice = invoice
        super(PaymentNode, self).__init__(invoice.client,
                                          invoice.uri + 'payments/',
                                          Payment)

    @property
    def invoice(self):
        '''
        Gets the parent invoice.
        @return: InvoiceBase
        '''
        return self.__invoice


    def add(self, payment_date, method, amount=None):
        '''
        Records a payment.
        @param payment_date:datetime date of the payment.
        @param method:str Payment method.
        @param amount:float (optional) Amount to transfer.
        @returns: Payment
        '''
        amount = amount or self.invoice.total

        request = Request(self.invoice.client, method="POST", uri=self.uri,
                          data={'date': payment_date, 'method': method,
                                'amount': amount})

        response = request.get_response()
        if response.get_status_code() == 201:
            payment_id = extract_id_from_uri(response["Location"])
            payment = self[payment_id]
            payment.sync(response.data, response["Etag"])
            self.invoice.load()
            return payment


class AnalyticsBase(Resource):
    '''
    Represents a resource holding a history for different currencies.
    '''
    def __getitem__(self, currency_code):
        '''
        Gets stats about the exchanges made with a specific currency.
        @param currency_code:str 3 letters ISO Currency code.
        @return: dict
        '''
        return self.get_currency_metrics(currency_code)

    def get_currency_metrics(self, currency_code):
        '''
        Gets stats about the exchanges made with a specific currency.
        @param currency_code:str 3 letters ISO Currency code.
        @return: dict
        '''
        if currency_code not in self.available_currencies:
            raise ValueError("Data is not available in " + currency_code)

        return CurrencyMetrics(currency_code.upper(),
                               self._get_attribute(currency_code.upper()))

    @property
    def available_currencies(self):
        '''
        Gets the list of currencies for which a digest is available.
        @return: list
        '''
        return self._get_attribute('currencies')

    @property
    def name(self):
        '''
        Gets the name of the entity for which the current data has been digested.
        @return: str
        '''
        return self._get_attribute('name')

    @property
    def email(self):
        '''
        Gets the email address for which the current data has been digested.
        @return: str
        '''
        return self._get_attribute('email')

    @property
    def currencies(self):
        '''
        Gets the list of currencies used.
        @return: list
        '''
        return self._get_attribute("currencies")

    @property
    def invoices_count(self):
        '''
        Gets the number of invoices exchanged.
        @return: int
        '''
        return self._get_attribute("invoicesCount")


class TimespanDigest(AnalyticsBase):
    '''
    Represents an analytics digest covering a specific time span.
    '''
    def __init__(self, entry, identifier):
        '''
        Initializes a new instance of the TimespanDigest class.
        @param entry:AnalyticsBase Parent analytics object.
        @param identifier:str ID of the object.
        '''
        super(TimespanDigest, self).__init__(entry.client, identifier)
        self._entry = entry

    @property
    def datetime(self):
        '''
        Gets the date and time covered by this digest.
        @return: datetime 
        '''
        return timestamp_to_datetime(self.id)


class TimespanDigestNode(Node):
    '''
    Represents an API node giving access to messages.
    '''
    def __init__(self, entry, uri_suffix, resource_cls):
        '''
        Initializes a new instance of the MessageNode
        @param thread: ThreadBase instance.
        @param resource_cls: Class Message class.
        '''
        self.__entry = entry
        super(TimespanDigestNode, self).__init__(entry.client,
                                              entry.uri + uri_suffix + '/',
                                              resource_cls)

    def get(self, identifier, default=None, **kwargs):
        '''
        Gets a buyer by its ID.
        @param identifier:ID of the buyer.
        @return: Buyer
        '''
        return super(TimespanDigestNode, self).get(self.__entry, identifier,
                                                   default=default, **kwargs)


class DailyDigest(TimespanDigest):
    '''
    Represents daily spanning over a day.
    '''
    @property
    def uri(self):
        '''
        Gets the URI
        @return: str
        '''
        return self._entry.uri + 'days/' + self.id


class HourlyDigest(TimespanDigest):
    '''
    Represents daily spanning over an hour.
    '''
    @property
    def uri(self):
        '''
        Gets the URI
        @return: str
        '''
        return self._entry.uri + 'hours/' + self.id


class Balance(Resource):
    '''
    Represents the balance of a user in a specific currency.
    '''
    def __init__(self, user, currency):
        '''
        Initializes a new instance of the Balance class.
        @param:User user
        @param currency:str Currency code.
        '''
        currency = currency.upper()
        if len(CURRENCIES) and currency not in CURRENCIES:
            raise ValueError('Invalid currency code')

        self.__user = user
        super(Balance, self).__init__(user.client, currency)

        self.__transactions = TransactionNode(self)

    @property
    def uri(self):
        '''
        Gets the URI of the balance
        @returns: str
        '''
        return '%balances/%s' % (self.__user.uri, self.currency)

    @property
    def user(self):
        '''
        Gets the user to which the current balance belongs
        @returns:User
        '''
        return self.__user

    @property
    def currency(self):
        '''
        Gets the currency in which the current balance is labeled
        @return: str
        '''
        return self.id

    @property
    def amount(self):
        '''
        Gets the balance position
        @return: float
        '''
        return self._get_attribute('amount')

    @property
    def transactions(self):
        '''
        Gets the transactions attached to this balance.
        @return: TransactionNode
        '''
        return self.__transactions


class Transaction(Resource):
    '''
    Represents a payment transaction attached to a specific balance.
    '''
    def __init__(self, balance, identifier):
        '''
        Initializes a new instance of the Transaction class.
        @param balance:Balance instance.
        @param identifier:str ID
        '''
        self.__balance = balance
        super(Transaction, self).__init__(balance.client, identifier)

    @property
    def uri(self):
        '''
        Gets the URI of the transaction
        @return: str
        '''
        return '%stransactions/%s/' % (self.__balance.uri, self.id)

    @property
    def balance(self):
        '''
        Gets the balance from which the transaction originated.
        @return: Balance
        '''
        return self.__balance

    @property
    def status(self):
        '''
        Gets the status of the transaction.
        @return: str
        '''
        return self._get_attribute('status')

    def __get_rank(self):
        '''
        Gets the priority rank of the transaction.
        @return: str
        '''
        if self.status != TRANSACTION_STATUS_PENDING:
            return ValueError('Rank\'s only available for pending transactions')

        return self._get_attribute('rank')

    def __set_rank(self, value):
        '''
        Sets the processing rank of the transaction.
        @param value:int Rank
        '''
        if self.status != TRANSACTION_STATUS_PENDING:
            return ValueError('Rank\'s only available for pending transactions')

        self._register_update('rank', value)

    @property
    def type(self):
        '''
        Gets the transaction type.
        @return: str
        '''
        return self._get_attribute('type')

    @property
    def eta(self):
        '''
        Gets the ETA of the transaction
        @return: datetime
        '''
        return self._get_date_attribute('eta')

    @property
    def invoices(self):
        '''
        Gets the status of the transaction.
        @return: str
        '''
        if self.type is not TRANSACTION_TYPE_PAYMENT:
            return []

        return [InvoiceBase.from_uri(self.balance.user, uri)
                for uri in self._get_attribute('invoices')]

    rank = property(__get_rank, __set_rank)

    @classmethod
    def from_uri(cls, user, uri):
        '''
        Instantiates a Transaction class instance using a URI.
        @param user:User instance
        @param uri:str URI
        @return: Transaction
        '''
        match = re.compile('^' + user.uri +
                           'balances\/(?P<currency>[a-z]{3})\/transactions' +
                           '\/(?P<id>\d+)\/$',
                           re.IGNORECASE).match(uri)

        if not match:
            return

        return cls(user.balances[match.groupdict()['currency']],
                   match.groupdict()['id'])


class TransactionNode(Node):
    '''
    Node giving access to transactions.
    '''
    def __init__(self, balance):
        '''
        Initializes a new instance of TransactionNode class.
        '''
        self.__balance = balance
        super(TransactionNode, self).__init__(balance.client,
                                              balance.uri + 'transactions/',
                                              Transaction)

    @property
    def balance(self):
        '''
        Gets the balance to which the transactions are attached.
        @return: Balance
        '''
        return self.__balance

    def __create_transaction(self, trans_type, **data):
        '''
        Creates a transaction to perform a payment or a withdrawal.
        @param trans_type:str Transaction type.
        @return: Transaction
        '''
        request = Request(self.balance.client, method="POST", uri=self.uri,
                          data=data)

        response = request.get_response()
        if response.get_status_code() == 201:
            transaction_id = extract_id_from_uri(response["Location"])
            transaction = self[transaction_id]
            transaction.sync(response.data, response["Etag"])
            return transaction

    def pay(self, invoices):
        '''
        Creates a transaction to pay one or multiple invoices using
        the parent balance.
        @param invoices:iterable
        @return: Transaction
        '''
        return self.__create_transaction(trans_type=TRANSACTION_TYPE_PAYMENT,
                                         invoices=[i.uri for i in invoices])

    def withdrawal(self, amount):
        '''
        Creates a transaction to withdrawal a specific amount of money
        from the parent balance.
        @param amount:float
        @return: Transaction
        '''
        return self.__create_transaction(trans_type=TRANSACTION_TYPE_WITHDRAWAL,
                                         amount=amount)
