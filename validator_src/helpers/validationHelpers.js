const { logError, logValidField } = require('./loggingHelpers.js');
const { logValidFieldsFlag } = require('./cloudHelpers.js');

function checkType(schemaObject, key, dataToValidate, parentPath = '', eventName, eventId, rootData) {
	const expected = schemaObject[key].type;
	const fieldPath = parentPath ? `${parentPath}.${key}` : key;
	const actual = Array.isArray(dataToValidate[key]) ? 'array' : typeof dataToValidate[key];
	const _root = rootData || dataToValidate;

	if (expected === 'string') {
		const value = dataToValidate[key];
		const isOptional = schemaObject[key]?.optional === true || schemaObject[key]?.required === false;

		if (isOptional && (value === undefined || value === null)) {
			return;
		}
		if (typeof value !== 'string') {
			logError(fieldPath, 'type', 'string', typeof value, eventName, _root, eventId);
			return;
		}
		if (value.trim() === '') {
			if (isOptional) {
				return;
			}
			logError(fieldPath, 'type', 'non-empty string', 'empty string', eventName, _root, eventId);
			return;
		}

		logValidField(fieldPath, expected, 'valid', logValidFieldsFlag, eventId, eventName);
		return;
	}

	if (expected === 'array') {
		if (!Array.isArray(dataToValidate[key])) {
			logError(fieldPath, 'type', expected, actual, eventName, _root, eventId);
			return;
		}
		if (schemaObject[key].nestedSchema) {
			dataToValidate[key].forEach((nestedItem, index) => {
				const itemPath = `${fieldPath}[${index}]`;
				if (typeof nestedItem !== 'object' || nestedItem === null) {
					checkWithSchema(schemaObject[key].nestedSchema, { '': nestedItem }, itemPath, eventName, eventId, _root);
				} else {
					checkWithSchema(schemaObject[key].nestedSchema, nestedItem, itemPath, eventName, eventId, _root);
				}
			});
			return;
		}
		logValidField(fieldPath, expected, 'valid', logValidFieldsFlag, eventId);
		return;
	}

	if (expected === 'object') {
		const val = dataToValidate[key];
		const valType = Array.isArray(val) ? 'array' : typeof val;

		if (val === null || Array.isArray(val) || valType !== 'object') {
			logError(fieldPath, 'type', expected, valType, eventName, _root, eventId);
			return;
		}
		if (schemaObject[key].nestedSchema) {
			checkWithSchema(schemaObject[key].nestedSchema, val, fieldPath, eventName, eventId, _root);
			return;
		}
		logValidField(fieldPath, expected, 'valid', logValidFieldsFlag, eventId);
		return;
	}

	if (actual !== expected) {
		logError(fieldPath, 'type', expected, actual, eventName, _root, eventId);
	} else {
		logValidField(fieldPath, expected, 'valid', logValidFieldsFlag, eventId, eventName);
	}
}

function checkLength(schemaObject, key, dataToValidate, parentPath = '', eventName, eventId, rootData) {
	const expectedLength = parseInt(schemaObject[key].length);
	const actualLength = (dataToValidate[key] || []).length;
	const fieldPath = parentPath ? `${parentPath}.${key}` : key;
	const _root = rootData || dataToValidate;

	if (actualLength !== expectedLength) {
		logError(fieldPath, 'length', expectedLength, actualLength, eventName, _root, eventId);
	}
}

function checkValue(schemaObject, keyRaw, dataToValidate, parentPath = '', eventName, eventId, rootData) {
	let key = keyRaw;
	let method = 'exact';
	if (keyRaw.startsWith('*')) {
		key = keyRaw.substring(1);
		method = 'contains';
	}
	const expected = schemaObject[keyRaw].value;
	const actual = dataToValidate[key];
	const fieldPath = parentPath ? `${parentPath}.${key}` : key;
	const _root = rootData || dataToValidate;

	if (method === 'contains' && (!actual || !actual.toString().includes(expected))) {
		logError(fieldPath, 'value_contains', expected, actual, eventName, _root, eventId);
	} else if (method === 'exact' && actual?.toString() !== expected?.toString()) {
		logError(fieldPath, 'value', expected, actual, eventName, _root, eventId);
	}
}

function checkRegex(schemaObject, key, dataToValidate, parentPath = '', eventName, eventId, rootData) {
	const regexPattern = schemaObject[key].regex;
	const pattern = new RegExp(regexPattern);
	const actual = dataToValidate[key];
	const fieldPath = parentPath ? `${parentPath}.${key}` : key;
	const _root = rootData || dataToValidate;

	if (typeof actual === "string" && actual.trim() === '' || actual === null) {
		logError(fieldPath, 'regex', regexPattern, 'empty_value', eventName, _root, eventId);
		return;
	}
	if (!pattern.test(actual)) {
		logError(fieldPath, 'regex', regexPattern, actual, eventName, _root, eventId);
	}
}


function checkWithSchema(schemaObject, dataToValidate, parentPath = '', eventName, eventId, rootData) {
	const _root = rootData || dataToValidate;

	for (const key in schemaObject) {
		if (key === 'version') continue;

		const rule = schemaObject[key];
		const fieldPath = parentPath ? `${parentPath}.${key}` : key;

		const hasKey = Object.prototype.hasOwnProperty.call(dataToValidate, key);
		const isOptional = rule.optional === true || rule.required === false;

		if (!hasKey) {
			if (isOptional) continue;
			logError(fieldPath, 'missing', 'field present', 'field missing', eventName, _root, eventId);
			continue;
		}

		const val = dataToValidate[key];
		const isEmptyString = typeof val === 'string' && val.trim() === '';

		if (isOptional && (val === undefined || val === null || isEmptyString)) {
			continue;
		}

		if (rule.hasOwnProperty('value'))
			checkValue(schemaObject, key, dataToValidate, parentPath, eventName, eventId, _root);
		if (rule.hasOwnProperty('type'))
			checkType(schemaObject, key, dataToValidate, parentPath, eventName, eventId, _root);
		if (rule.hasOwnProperty('length'))
			checkLength(schemaObject, key, dataToValidate, parentPath, eventName, eventId, _root);
		if (rule.hasOwnProperty('regex'))
			checkRegex(schemaObject, key, dataToValidate, parentPath, eventName, eventId, _root);
	}
}

exports.checkType = checkType;
exports.checkLength = checkLength;
exports.checkValue = checkValue;
exports.checkRegex = checkRegex;
exports.checkWithSchema = checkWithSchema;
