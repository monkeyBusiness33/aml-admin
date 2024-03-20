from rest_framework.authentication import TokenAuthentication


class BearerTokenAuthentication(TokenAuthentication):
    '''
    Subclass of the 'TokenAuthentication' to use 'Bearer' token keyword.
    '''

    keyword = 'Bearer'
