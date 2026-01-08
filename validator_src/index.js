
const functions = require('@google-cloud/functions-framework');
const { resetLogs } = require('./helpers/loggingHelpers.js');
const { v4: uuidv4 } = require('uuid');

const { checkWithSchema } = require('./helpers/validationHelpers.js');
const { logPassed } = require('./helpers/loggingHelpers.js');
const { errorLogEntries, validLogEntries, validFieldsEntries } = require('./helpers/loggingHelpers.js');
const { loadJsonFromGCS, logEventsToBigquery, BQ_DATASET, BQ_TABLE, BUCKET_NAME  } = require('./helpers/cloudHelpers.js');

const eventNameAttrEnv = process.env.EVENT_NAME_ATTRIBUTE;
const eventNameAttribute = (eventNameAttrEnv ? eventNameAttrEnv.trim() : 'event_name');

const eventDataPathEnv = process.env.EVENT_DATA_PATH;
const eventDataPath = eventDataPathEnv === undefined ? 'data' : eventDataPathEnv.trim();


exports.validateEvent = (req, res) => {
  const eventId = uuidv4();

  const body = req?.body || {};
  const eventData = getByPath(body, eventDataPath);

  if (!BUCKET_NAME || !BQ_DATASET || !BQ_TABLE) {
    console.error('Missing GCP configuration:\n', 'Bucket:', BUCKET_NAME, 'Dataset:', BQ_DATASET, 'Table:', BQ_TABLE);
    return res.status(400).send({ status: 'config_error', message: 'Function configuration is incomplete' });
  }
  if (!req.body) {
    console.error('Invalid request body. No body present.');
    return res.status(400).send({ status: 'invalid_request', message: 'No request body present' });
  }
  if (!eventData || typeof eventData !== 'object') {
    console.error('Invalid request body. No event data present. Data expected at:', eventDataPath || '(root)');
    console.log('received:');
    console.dir(req.body, { depth: 1 });
    return res.status(400).send({ status: 'invalid_request', message: `No event data found at path: ${eventDataPath || '(root)'}` });
  }

  const eventName = getByPath(eventData, eventNameAttribute);
  if (!eventName) {
    console.error(`Invalid request body.\nMissing: eventNameAttribute "${eventNameAttribute}" in payload.`);
    return res.status(400).send({ status: 'invalid_request', message: `Missing eventNameAttribute "${eventNameAttribute}" in payload` });
  }

  loadJsonFromGCS(`${eventName}.json`)
    .then((masterSchema) => {
      if (!masterSchema) {
        console.error('No valid schema found for', eventName);
        return res.status(404).send({ status: 'schema_not_found', message: `Schema not found for event: ${eventName}` });
      }
      try {
        checkWithSchema(masterSchema, eventData, '', eventName, eventId);

        if (errorLogEntries.length > 0) {
          console.log('Validation errors found:', errorLogEntries);
          logEventsToBigquery(errorLogEntries);
          logEventsToBigquery(validFieldsEntries);
          return res.status(400).send({
            status: 'validation_failed',
            message: 'Validation errors occurred',
            errorsLogged: errorLogEntries.length,
          });
        } else {
          logPassed(eventId, eventName);
          if (validLogEntries.length > 0) {
            console.log('Valid events found:', validLogEntries);
            logEventsToBigquery(validLogEntries);
            logEventsToBigquery(validFieldsEntries);
            return res.status(200).send({
              status: 'event valid',
              eventsLogged: validLogEntries.length,
            });
          }
          return res.status(200).send({ status: 'event valid', eventsLogged: 0 });
        }
      } catch (err) {
        console.error('Error during validation or logging:', err);
        return res.status(500).send({ status: 'error', message: 'Internal server error' });
      }
    })
    .catch((err) => {
      console.error('Error loading schema from GCS:', err);
      return res.status(500).send({ status: 'error', message: 'Internal server error' });
    });

  resetLogs();
};

function getByPath(obj, path) {
  if (path == null || path === '') return obj;

  const pathArr = Array.isArray(path)
    ? path
    : String(path)
        .trim()
        .replace(/\[(\w+)\]/g, '.$1')
        .replace(/^\./, '')          
        .split('.')
        .filter(Boolean);

  return pathArr.reduce((acc, key) => (acc != null ? acc[key] : undefined), obj);
}
exports.eventNameAttribute = eventNameAttribute;