
const errorLogEntries = [];
const validLogEntries = [];
const validFieldsEntries = [];
const logPayloadWhenErrorFlag = process.env.LOG_PAYLOAD_WHEN_ERROR;
const logPayloadWhenValidFlag = process.env.LOG_PAYLOAD_WHEN_VALID;
function logError(field, type, expected, actual, eventName, eventData, eventId) {
    errorLogEntries.push({
        event_name: eventName,
        event_id: eventId,
        field,
        error_type: type,
        expected: expected?.toString(),
        actual: actual?.toString(),
        timestamp: new Date().toISOString(),
        status: 'error',
        date_utc: new Date().toISOString().split('T')[0],
        event_data: logPayloadWhenErrorFlag === "true" ? JSON.stringify(eventData) : null
    });
}

function logPassed(eventId, eventName, eventData) {
    validLogEntries.push({
        event_name: eventName,
        event_id: eventId,
        timestamp: new Date().toISOString(),
        status: 'valid',
        date_utc: new Date().toISOString().split('T')[0],
        event_data: logPayloadWhenValidFlag === "true" ? JSON.stringify(eventData) : null
    });
}

function logValidField(field, value, status, logValidFieldsFlag, eventId, eventName, eventData) {
    if (logValidFieldsFlag === true) { 
        validFieldsEntries.push({
            event_name: eventName,
            event_id: eventId,
            field,
            value: JSON.stringify(value),
            timestamp: new Date().toISOString(),
            status: status,
            date_utc: new Date().toISOString().split('T')[ 0 ],
            event_data: logPayloadWhenValidFlag === "true" ? JSON.stringify(eventData) : null
        });
    } else return
}
function resetLogs() {
  errorLogEntries.length = 0;
  validLogEntries.length = 0;
  validFieldsEntries.length = 0;
}

exports.logError = logError;
exports.logPassed = logPassed;
exports.logValidField = logValidField;
exports.errorLogEntries = errorLogEntries;
exports.validLogEntries = validLogEntries;
exports.validFieldsEntries = validFieldsEntries;
exports.resetLogs = resetLogs;