from flask import Blueprint

status = Blueprint('status', __name__, url_prefix='/status')


@status.route('/')
def get_status():
    """ Check if the API is running.
    ---
    responses:
      200:
        description: The API is running.
        content:
          application/json:
            schema:
              $ref: '#/definitions/ApiStatus'
    definitions:
      ApiStatus:
        type: object
        properties:
          status:
            type: string
            description: The API is running
            enum:
              - active
    """
    return {
        'status': 'active'
    }
