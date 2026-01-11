
swagger: '2.0'
info:
  title: events-validator-api
  version: 1.0.0
schemes:
  - https
produces:
  - application/json
paths:
  /eventsValidator:
    post:
      summary: validateEvents
      operationId: eventsValidator
      x-google-backend:
        address: ${run_uri}
        jwt_audience: ${run_uri}

      security:
        - api_key: [${api_key}]
      parameters:
        - in: body
          name: payload
          required: true
          schema:
            type: object
      responses:
        '200':
          description: OK
          schema:
            type: string
securityDefinitions:
  api_key:
    type: apiKey
    name: key
    in: query
