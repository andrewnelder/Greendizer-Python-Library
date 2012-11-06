# -*- coding: utf-8 -*-
import logging
from greendizer.clients.helpers import Address
from greendizer.clients.base import (extract_id_from_uri, size_in_bytes)
from greendizer.clients.http import Request
from greendizer.clients.dal import Node
from greendizer.clients.resources import (User, EmailBase, InvoiceBase,
                                  InvoiceNodeBase, AnalyticsBase, DailyDigest,
                                  HourlyDigest, TimespanDigestNode)


XMLI_MIMETYPE = 'application/xml'
MAX_INVOICE_CONTENT_LENGTH = 5*1024  # 5kb


class ResourceNotFoundException(Exception):
    '''
    Represents the exception raised if a resource could not be found.
    '''
    pass


class Seller(User):
    '''
    Represents a seller user
    '''
    def __init__(self, client):
        '''
        Initializes a new instance of the Seller class.
        '''
        super(Seller, self).__init__(client)
        self.__emailNode = EmailNode(self)
        self.__buyerNode = BuyerNode(self)

    @property
    def uri(self):
        '''
        Gets the URI of the seller.
        @return: str
        '''
        return "sellers/" + self.id + '/'

    @property
    def emails(self):
        '''
        Gets access to the seller's registered email addresses.
        @return: EmailNode
        '''
        return self.__emailNode

    @property
    def buyers(self):
        '''
        Gets access to the seller's customers.
        @return: BuyerNode
        '''
        return self.__buyerNode


class EmailNode(Node):
    '''
    Represents an API node giving access to emails.
    '''
    def __init__(self, seller):
        '''
        Initializes a new instance of the EmailNode class.
        @param seller:Seller Currently authenticated seller.
        '''
        self.__seller = seller
        super(EmailNode, self).__init__(seller.client, seller.uri + "emails/",
                                        Email)

    def get(self, identifier, **kwargs):
        '''
        Gets an email by its ID.
        @param identifier:str ID of the email address.
        @return: Email
        '''
        return super(EmailNode, self).get(self.__seller, identifier, **kwargs)


class Email(EmailBase):
    '''
    Represents an email address.
    '''
    def __init__(self, *args, **kwargs):
        '''
        Initializes a new instance of the Email class.
        '''
        super(Email, self).__init__(*args, **kwargs)
        self.__invoiceNode = InvoiceNode(self)

    @property
    def invoices(self):
        '''
        Gets access to the invoices sent with the current email address.
        @return: greendizer.dal.Node
        '''
        return self.__invoiceNode


class InvoiceNode(InvoiceNodeBase):
    '''
    Represents an API node giving access to the invoices sent by the currently
    authenticated seller.
    '''
    def __init__(self, email):
        '''
        Initializes a new instance of the InvoiceNode class.
        @param email:Email instance.
        '''
        super(InvoiceNode, self).__init__(email, Invoice)

    @property
    def outbox(self):
        '''
        Gets a collection to manipulate the invoices in the outbox.
        @return: Collection
        '''
        return self.search(query="location==0")

    def get_by_custom_id(self, custom_id):
        '''
        Gets an invoice using its custom_id
        @param custom_id:str Custom ID of the invoice to retrieve
        '''
        if not custom_id:
            raise ValueError("Invalid custom_id parameter")

        collection = self.search(query="customId==" + custom_id)
        collection.populate(offset=0, limit=1)
        if not len(collection):
            raise ResourceNotFoundException("Could not find invoice with " \
                                            "custom_id " + custom_id)

        return collection[0]
    
    def send(self, invoice, signature=True):
        '''
        Sends an invoice
        @param invoices:list List of invoices to send.
        @return: InvoiceReport
        '''
        from pyxmli import Invoice as XMLiInvoice
        if not issubclass(invoice.__class__, XMLiInvoice):
            raise ValueError('\'invoice\' is not an instance of ' \
                             'pyxmli.Invoice or one of its subclasses.')
        private_key, public_key = self.email.client.keys
        enable_signature = signature and private_key and public_key
        if enable_signature != signature:
            logging.warn('Missing private and/or public key(s). Invoices ' \
                         'will not be signed.') 
        
        '''
        Filling the invoice with information about the seller.
        '''        
        if not invoice.identifier:
            import uuid
            invoice.identifier = str(uuid.uuid1())
        
        invoice.seller.identifier = self.email.id
        invoice.seller.name = self.email.user.company.name
        address = self.email.user.company.address
        invoice.seller.address.street_address = address.street_address
        invoice.seller.address.city = address.city
        invoice.seller.address.zipcode = address.zipcode
        invoice.seller.address.state = address.state
        invoice.seller.address.country = address.country
        invoice.mentions = (invoice.mentions or
                            self.email.user.company.legal_mentions)
            
        data = (invoice.to_signed_str(private_key, public_key) 
                if enable_signature else invoice.to_string())
            
        if size_in_bytes(data) > MAX_INVOICE_CONTENT_LENGTH:
            raise Exception('An invoice cannot be more than %dkb.' %
                            MAX_INVOICE_CONTENT_LENGTH)
        
        request = Request(client=self.email.client,
                          method='POST',
                          uri=self._uri,
                          data=data,
                          content_type=XMLI_MIMETYPE, )
        
        response = request.get_response()
        #FIX: Bug in the API. Should only return 201.
        if response.status_code in [200, 201]:
            return self[response.data["id"]]


class Invoice(InvoiceBase):
    '''
    Represents an invoice.
    '''
    def __init__(self, *args, **kwargs):
        '''
        Initializes a new instance of the Invoice class.
        '''
        super(Invoice, self).__init__(*args, **kwargs)
        self.__buyer_address = None
        self.__buyer_delivery_address = None

    @property
    def custom_id(self):
        '''
        Gets the custom ID set in the initial XMLi
        @return: str
        '''
        return self._get_attribute("customId")

    @property
    def buyer_name(self):
        '''
        Gets the buyer's name as specified on the invoice.
        @return: str
        '''
        return (self._get_attribute("buyer") or {}).get("name")

    @property
    def buyer_email(self):
        '''
        Gets the buyer's name as specified on the invoice.
        @return: str
        '''
        return (self._get_attribute("buyer") or {}).get("email")

    @property
    def buyer_address(self):
        '''
        Gets the delivery address of the buyer.
        @return: Address
        '''
        address = (self._get_attribute("buyer") or {}).get("address")
        if not self.__buyer_address and address:
            self.__buyer_address = Address(address)

        return self.__buyer_address

    @property
    def buyer_delivery_address(self):
        '''
        Gets the delivery address of the buyer.
        @return: Address
        '''
        address = (self._get_attribute("buyer") or {}).get("delivery")
        if not self.__buyer_delivery_address and address:
            self.__buyer_delivery_address = Address(address)

        return self.__buyer_delivery_address

    @property
    def buyer(self):
        '''
        Gets the buyer.
        @return: Buyer
        '''
        buyer_uri = (self._get_attribute("buyer") or {}).get("uri")
        return self.client.seller.buyers[extract_id_from_uri(buyer_uri)]

    def cancel(self):
        '''
        Cancels the invoice.
        '''
        self._register_update("canceled", True)
        self.update()


class BuyerNode(Node):
    '''
    Represents an API node giving access to info about the customers.
    '''
    def __init__(self, seller):
        '''
        Initializes a new instance of the BuyerNode class.
        @param seller:Seller Currently authenticated seller.
        '''
        self.__seller = seller
        super(BuyerNode, self).__init__(seller.client,
                                        seller.uri + "buyers/",
                                        Buyer)

    def get(self, identifier, **kwargs):
        '''
        Gets a buyer by its ID.
        @param identifier:ID of the buyer.
        @return: Buyer
        '''
        return super(BuyerNode, self).get(self.__seller, identifier, **kwargs)


class Buyer(AnalyticsBase):
    '''
    Represents a customer of the seller.
    '''
    def __init__(self, seller, identifier):
        '''
        Initializes a new instance of the Buyer class.
        '''
        self.__seller = seller
        self.__address = None
        self.__delivery_address = None
        super(Buyer, self).__init__(seller.client, identifier)
        self.__days = TimespanDigestNode(self, 'days/', DailyDigest)
        self.__hours = TimespanDigestNode(self, 'hours/', HourlyDigest)


    @property
    def days(self):
        '''
        Gets access to daily digests of analytics.
        @return: Node
        '''
        return self.__days


    @property
    def hours(self):
        '''
        Gets access to hourly digests of analytics.
        @return: Node
        '''
        return self.__hours

    @property
    def seller(self):
        '''
        Gets the currently authenticated seller.
        @return: Seller
        '''
        return self.__seller

    @property
    def billing_address(self):
        '''
        Gets the address of the buyer.
        @return: Address
        '''
        if not self.__address and self._get_attribute("address"):
            self.__address = Address(self._get_attribute("address"))

        return self.__address

    @property
    def delivery_address(self):
        '''
        Gets the delivery address of the buyer.
        @return: Address
        '''
        if not self.__delivery_address and self._get_attribute("delivery"):
            self.__delivery_address = Address(self._get_attribute("delivery"))

        return self.__delivery_address

    @property
    def name(self):
        '''
        Gets the name of the buyer.
        @return: str
        '''
        return self._get_attribute("name")

    @property
    def uri(self):
        '''
        Gets the URI of the resource.
        @return: str
        '''
        return "%sbuyers/%s/" % (self.__seller.uri, self.id)
