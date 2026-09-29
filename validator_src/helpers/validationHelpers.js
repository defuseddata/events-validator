const { logError, logValidField } = require('./loggingHelpers.js');
const { logValidFieldsFlag } = require('./cloudHelpers.js');

function checkType(schemaObject, key, dataToValidate, parentPath = '', eventName, eventId, rootData, getByPathFn) {
	const expected = schemaObject[key].type;
	const fieldPath = parentPath ? `${parentPath}.${key}` : key;
	const actual = Array.isArray(dataToValidate[key]) ? 'array' : typeof dataToValidate[key];
	const _root = rootData || dataToValidate;
	const isOptional = schemaObject[key].optional === true || schemaObject[key].required === false;

	if (expected === 'string') {
		const value = dataToValidate[ key ];
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

		logValidField(fieldPath, expected, 'valid', logValidFieldsFlag, eventId, eventName, _root);
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
					// Handling array of primitives if nestedSchema defined? 
					// Usually nestedSchema implies array of objects.
					// If array of strings, schema structure might be different.
					// Assuming array of objects for nestedSchema presence.
					checkWithSchema(schemaObject[key].nestedSchema, { '': nestedItem }, itemPath, eventName, eventId, _root, getByPathFn);
				} else {
					checkWithSchema(schemaObject[key].nestedSchema, nestedItem, itemPath, eventName, eventId, _root, getByPathFn);
				}
			});
			return;
		}
		logValidField(fieldPath, expected, 'valid', logValidFieldsFlag, eventId, eventName, _root);
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
			checkWithSchema(schemaObject[key].nestedSchema, val, fieldPath, eventName, eventId, _root, getByPathFn);
			return;
		}
		logValidField(fieldPath, expected, 'valid', logValidFieldsFlag, eventId, eventName, _root);
		return;
	}

	if (actual !== expected) {
		logError(fieldPath, 'type', expected, actual, eventName, _root, eventId);
	} else {
		logValidField(fieldPath, expected, 'valid', logValidFieldsFlag, eventId, eventName, _root);
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

function checkValue(schemaObject, key, dataToValidate, parentPath = '', eventName, eventId, rootData) {
	const expected = schemaObject[key].value;
	const actual = dataToValidate[key];
	const fieldPath = parentPath ? `${parentPath}.${key}` : key;
	const _root = rootData || dataToValidate;

	if (actual?.toString() !== expected?.toString()) {
		logError(fieldPath, 'value', expected, actual, eventName, _root, eventId);
	}
}

function checkValueContains(schemaObject, key, dataToValidate, parentPath = '', eventName, eventId, rootData) {
	const rule = schemaObject[key];
	const expected = rule.value_contains;
	const actual = dataToValidate[key];
	const fieldPath = parentPath ? `${parentPath}.${key}` : key;
	const _root = rootData || dataToValidate;
	const caseSensitive = rule.value_contains_case_sensitive !== false;

	const actualStr = actual != null ? actual.toString() : '';
	const expectedStr = expected != null ? expected.toString() : '';
	const haystack = caseSensitive ? actualStr : actualStr.toLowerCase();
	const needle = caseSensitive ? expectedStr : expectedStr.toLowerCase();

	if (!actual || !haystack.includes(needle)) {
		logError(fieldPath, 'value_contains', expected, actual, eventName, _root, eventId);
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

function checkWithSchema(schemaObject, dataToValidate, parentPath = '', eventName, eventId, rootData, getByPathFn) {
	const _root = rootData || dataToValidate;

	for (const key in schemaObject) {
		if (key === 'version') continue;

		const rule = schemaObject[key];
		const fieldPath = parentPath ? `${parentPath}.${key}` : key;
		const isOptional = rule.optional === true || rule.required === false;
		if (rule.validate_if_present) {
            if (typeof getByPathFn === 'function') {
                const targetValue = getByPathFn(_root, rule.validate_if_present);
                if (targetValue === undefined || targetValue === null) {
                    continue;
                }
                if (!Object.prototype.hasOwnProperty.call(dataToValidate, key)) {
                     logError(
                        fieldPath,
                        'missing_conditional',
                        'field present',
                        'field missing',
                        eventName, _root, eventId
                     );
                     continue;
                }
            }
		}

		if (rule.validate_if) {
            if (typeof getByPathFn === 'function') {
                const conditionField = rule.validate_if.field;
                const expectedValues = Array.isArray(rule.validate_if.value) 
                                       ? rule.validate_if.value 
                                       : [rule.validate_if.value];
                
                const targetValue = getByPathFn(_root, conditionField);
                const isMatch = expectedValues.some(val => targetValue?.toString() === val?.toString());

                if (!isMatch) {
                    continue;
                }
                
                if (!Object.prototype.hasOwnProperty.call(dataToValidate, key)) {
                     logError(
                        fieldPath,
                        'missing_conditional',
                        // `field present,${conditionField}=${targetValue}`,
                        'field present',
                        'field missing',
                        eventName, _root, eventId
                     );
                     continue;
                }
            }
		}

		const hasKey = Object.prototype.hasOwnProperty.call(dataToValidate, key);

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

		if (rule.hasOwnProperty('value') && rule.value !== null)
			checkValue(schemaObject, key, dataToValidate, parentPath, eventName, eventId, _root);
		if (rule.hasOwnProperty('value_contains'))
			checkValueContains(schemaObject, key, dataToValidate, parentPath, eventName, eventId, _root);
		if (rule.hasOwnProperty('type'))
			checkType(schemaObject, key, dataToValidate, parentPath, eventName, eventId, _root, getByPathFn);
		if (rule.hasOwnProperty('length'))
			checkLength(schemaObject, key, dataToValidate, parentPath, eventName, eventId, _root);
		if (rule.hasOwnProperty('regex'))
			checkRegex(schemaObject, key, dataToValidate, parentPath, eventName, eventId, _root);
	}
}

exports.checkType = checkType;
exports.checkLength = checkLength;
exports.checkValue = checkValue;
exports.checkValueContains = checkValueContains;
exports.checkRegex = checkRegex;
exports.checkWithSchema = checkWithSchema;
