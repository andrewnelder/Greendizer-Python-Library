# -*- coding: utf-8 -*-
from greendizer.clients.base import extract_id_from_uri
from greendizer.clients.dal import Node
from greendizer.clients.resources import (User, Company, EmailBase,
                                  InvoiceBase, InvoiceNodeBase, AnalyticsBase,
                                  TimespanDigestNode, HourlyDigest, DailyDigest)


class Buyer(User):
    '''
    Represents a buyer user
    '''
    def __init__(self, client):
        '''
        Initializes a new instance of the Buyer class.
        @param client:greendizer.Client Client instance.
        '''
        super(Buyer, self).__init__(client)
        self.__emailNode = EmailNode(self)

    @property
    def emails(self):
        '''
        Gives access to the emails node.
        @return: EmailNode
        '''
        return self.__emailNode

    @property
    def uri(self):
        '''
        Gets the URI of the resource
        @return: str
        '''
        return "buyers/me/"


class Email(EmailBase):
    '''
    Represents an Email address from a buyer's perspective.
    '''
    def __init__(self, user, identifier):
        '''
        Initializes a new instance of the Email class.
        @param user:User Currently authenticated user.
        @param identifier:str ID of the email.
        '''
        self.__user = user
        super(Email, self).__init__(user, identifier)
        self.__invoiceNode = InvoiceNodeBase(self)
        self.__sellerNode = SellerNode(self)

    @property
    def invoices(self):
        '''
        Gets the node of invoices attached to the current email address.
        @return: InvoiceNode
        '''
        return self.__invoiceNode

    @property
    def sellers(self):
        '''
        Gets the
        '''
        return self.__sellerNode


class EmailNode(Node):
    '''
    Represents an API node giving access to the email accounts attached
    to the currently authenticated user.
    '''
    def __init__(self, user):
        '''
        Initializes a new instance of the EmailNode class.
        @param user:User Currenly authenticated user.
        @param uri:str URI of the node.
        @param resource_cls:Class Email class.
        '''
        self.__user = user
        super(EmailNode, self).__init__(user.client, user.uri + "emails/",
                                        Email)

    def get(self, identifier, **kwargs):
        '''
        Gets an email address by its ID.
        @param identifier:str ID of the email address.
        @return: Email
        '''
        return super(EmailNode, self).get(self.__user, identifier, **kwargs)


class Invoice(InvoiceBase):
    '''
    Represents an invoice from a buyer's perspective.
    '''
    @property
    def seller(self):
        '''
        Gets the seller who sent the invoice.
        @return: Seller
        '''
        seller_id = extract_id_from_uri(self._get_attribute("sellerURI"))
        return Seller(self.email, seller_id)


class InvoiceNode(InvoiceNodeBase):
    '''
    Represents an API node giving access to invoices sent to a specific email
    address.
    '''
    def __init__(self, email):
        '''
        Initializes a new instance of the InvoiceNode class.
        @param email:Email Parent email instance.
        '''
        self.__email = email
        super(InvoiceNode, self).__init__(email, Invoice)

    def get(self, identifier, **kwargs):
        '''
        Gets an invoice by its ID.
        @param identifier:str ID of the invoice.
        @return: Invoice
        '''
        return super(InvoiceNode, self).get(self.__email, identifier, **kwargs)


class Seller(AnalyticsBase):
    '''
    Represents a seller who has invoiced the currently authenticated user
    in the past.
    '''
    def __init__(self, email, identifier):
        '''
        Initializes a new instance of the Seller class.
        @param email:Email Parent email instance.
        @param identifier:str ID of the seller.
        '''
        self.__email = email
        super(Seller, self).__init__(email.client, identifier)
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
    def uri(self):
        '''
        Gets the URI of the seller.
        @return: str
        '''
        return "%ssellers/%s/" % (self.__email.uri, self.id)

    @property
    def email(self):
        '''
        Gets the parent email.
        @return: Email
        '''
        return self.__email

    @property
    def company(self):
        '''
        Gets the seller's company info.
        @return: greendizer.resources.Company
        '''
        company_id = extract_id_from_uri(self._get_attribute("companyURI"))
        return Company(self.__email, company_id)


class SellerNode(Node):
    '''
    Represents the node giving access to the history of exchanges that were
    made with the sellers.
    '''
    def __init__(self, email):
        '''
        Initializes a new instance of the SellerHistoryNode class.
        @param email:Email Parent email instance.
        '''
        self.__email = email
        super(SellerNode, self).__init__(email.client,
                                        email.uri + "sellers/",
                                        Seller)

    def get(self, identifier, **kwargs):
        '''
        Gets the history of a specific seller
        @param identifier:str ID of the seller.
        @return: Seller
        '''
        return super(SellerNode, self).get(self.__email, identifier, **kwargs)

    @property
    def email(self):
        '''
        Gets the parent email address.
        @return: Email
        '''
        return self.__email
