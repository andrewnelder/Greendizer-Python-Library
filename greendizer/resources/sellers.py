# -*- coding: utf-8 -*-
import logging
from datetime import timedelta
from greendizer.helpers import Address
from greendizer.base import (is_empty_or_none, extract_id_from_uri,
                             to_byte_string, size_in_bytes)
from greendizer.http import Request, MultipartRequest, MultipartRequestPart
from greendizer.dal import Resource, Node
from greendizer.resources import (User, EmailBase, InvoiceBase, ThreadBase,
                                  MessageBase, InvoiceNodeBase, AnalyticsBase,
                                  ThreadNodeBase, MessageNodeBase, DailyDigest,
                                  HourlyDigest, TimespanDigestNode)


XMLI_MIMETYPE = 'application/xmli+xml'
DISABLE_NOTIFICATION_HEADER = 'X-GD-DISABLE-NOTIFICATION'
MAX_INVOICES_PER_REQUEST = 100
MAX_INVOICE_CONTENT_LENGTH = 5*1024  # 500kb


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
        self.__threadNode = ThreadNode(self)
        self.__emailNode = EmailNode(self)
        self.__buyerNode = BuyerNode(self)

    @property
    def uri(self):
        '''
        Gets the URI of the seller.
        @return: str
        '''
        return "sellers/me/"

    @property
    def emails(self):
        '''
        Gets access to the seller's registered email addresses.
        @return: EmailNode
        '''
        return self.__emailNode

    @property
    def threads(self):
        '''
        Gets access to the conversation threads.
        @return: ThreadNode
        '''
        return self.__threadNode

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
    
    def send(self, invoices=[], signature=True):
        '''
        Sends an invoice
        @param invoices:list List of invoices to send.
        @return: InvoiceReport
        '''
        if len(invoices) > MAX_INVOICES_PER_REQUEST:
            raise ValueError('A request can only carry a maximum of %d ' /
                             'invoices' % MAX_INVOICES_PER_REQUEST)
        
        private_key, public_key = self.email.client.keys
        enable_signature = signature and private_key and public_key
        
        if enable_signature != signature:
            logging.warn('Missing private and/or public key. Invoices ' /
                         'will not be signed.') 

        parts = []
        for invoice in invoices:
            invoice.seller.name = self.email.user.company.name
            invoice.seller.email = self.email.id
            invoice.seller.address = self.email.user.company.address
            invoice.legal_mentions = (invoice.legal_mentions or
                                      self.email.user.company.legal_mentions)
            
            data = (invoice.to_signed_str(private_key, public_key) 
                    if enable_signature else invoice.to_string())
            
            if size_in_bytes(data) > MAX_CONTENT_LENGTH:
                raise Exception('An invoice cannot be more than %dkb.' %
                                MAX_INVOICE_CONTENT_LENGTH)
            
            part = MultipartRequestPart(content_type=XMLI_MIMETYPE, data=data)
            if invoice.disable_notification != None:
                part.headers.update({DISABLE_NOTIFICATION_HEADER:
                                     invoice.disable_notification})
            
            parts.append(part)
            
        request = MutlipartRequest(self.email.client, self._uri, parts)
        response = request.get_response()
        if response.status_code == 202:  # Accepted
            return InvoiceReport(self.email,
                                 extract_id_from_uri(response["Location"]))


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


class InvoiceReportNode(Node):
    '''
    Represents an API node giving access to invoice reports.
    '''
    def __init__(self, email):
        '''
        Initializes a new instance of the InvoiceReportNode class.
        @param email:Email Email instance.
        '''
        self.__email = email
        super(InvoiceReportNode, self).__init__(email.client,
                                                email.uri + "invoices/reports/",
                                                InvoiceReport)

    def get(self, identifier, **kwargs):
        '''
        Gets an invoice report by its ID.
        @param identifier:str ID of the invoice report.
        @return: InvoiceReport
        '''
        return super(InvoiceReportNode, self).get(self.__email, identifier,
                                                  **kwargs)


class InvoiceReport(Resource):
    '''
    Represents an invoice delivery report.
    '''
    def __init__(self, email, identifier):
        '''
        Initializes a new instance of the InvoiceReport class.
        @param email:Email Email instance.
        @param identifier:str ID of the report.
        '''
        self.__email = email
        super(InvoiceReport, self).__init__(email.client, identifier)

    @property
    def email(self):
        '''
        Email address from which the invoices were sent.
        @return: Email
        '''
        return self.__email

    @property
    def uri(self):
        '''
        Returns the URI of the resource.
        @return: str
        '''
        return "%sinvoices/reports/%s/" % (self.__email.uri, self.id)

    @property
    def state(self):
        '''
        Gets a value indicating the stage of processing.
        @return: int
        '''
        return self._get_attribute("state") or 0

    @property
    def ip_address(self):
        '''
        Gets the IP Address of the machine which sent the request.
        @return: str
        '''
        return self._get_attribute("ipAddress")

    @property
    def hash(self):
        '''
        Gets the computed hash of the invoices received.
        @return: str
        '''
        return self._get_attribute("hash")

    @property
    def error(self):
        '''
        Gets a description of the error encountered if any.
        @return: str
        '''
        return self._get_attribute("error")

    @property
    def start(self):
        '''
        Gets the date and time on which the processing started.
        @return: datetime
        '''
        return self._get_date_attribute("startTime")

    @property
    def end(self):
        '''
        Gets the date and time on which the processing ended.
        @return: datetime
        '''
        return (self.start
                + timedelta(milliseconds=self._get_attribute("elapsedTime")))

    @property
    def invoices_count(self):
        '''
        Gets the number of invoices being processed.
        @return: int
        '''
        return self._get_attribute("invoicesCount")


class MessageNode(MessageNodeBase):
    '''
    Represents an API node giving access to messages.
    '''
    def __init__(self, thread):
        '''
        Initializes a new instance of the MessageNode class.
        @param thread: Thread  Thread instance
        '''
        super(MessageNode, self).__init__(thread, Message)


class Message(MessageBase):
    '''
    Represents a conversation thread message.
    '''
    @property
    def buyer(self):
        '''
        Gets the buyer.
        @return: Buyer
        '''
        if not self.is_from_current_user:
            buyer_id = extract_id_from_uri(self._get_attribute("buyerURI"))
            return self.thread.seller.buyers[buyer_id]


class ThreadNode(ThreadNodeBase):
    '''
    Represents a node giving access to conversation threads from a seller's
    perspective.
    '''
    def __init__(self, seller):
        '''
        Initializes a new instance of the SellersThreadNode class.
        @param seller:Seller Current seller instance.
        '''
        self.__seller = seller
        super(ThreadNode, self).__init__(seller.client,
                                         seller.uri + "threads/",
                                         Thread)

    def get(self, identifier, **kwargs):
        '''
        Gets a thread by its ID.
        @param identifier:str ID of the thread.
        @return: Thread.
        '''
        return super(ThreadNode, self).get(self.__seller, identifier, **kwargs)

    @property
    def seller(self):
        '''
        Gets the current user
        @return: Seller
        '''
        return self.__seller


class Thread(ThreadBase):
    '''
    Represents a conversation thread.
    '''
    def __init__(self, seller, identifier):
        '''
        Initializes a new instance of the Thread class.
        @param seller:Seller Seller instance.
        @param identifier:str ID of the thread.
        '''
        self.__seller = seller
        super(Thread, self).__init__(seller.client, identifier)
        self.__messageNode = MessageNode(self)

    @property
    def uri(self):
        '''
        Returns the URI of the resource.
        @return: str
        '''
        return "%sthreads/%s/" % (self.__seller.uri, self.id)

    @property
    def messages(self):
        '''
        Gets access to the messages of the thread.
        @return: MessageNode
        '''
        return self.__messageNode


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
