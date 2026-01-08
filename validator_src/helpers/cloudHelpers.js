const { Storage } = require('@google-cloud/storage');
const { BigQuery } = require('@google-cloud/bigquery');

const storage = new Storage();
const bigquery = new BigQuery();

const BUCKET_NAME = process.env.SCHEMA_BUCKET;
const BQ_DATASET = process.env.BQ_DATASET;
const BQ_TABLE = process.env.BQ_TABLE;
const logValidFieldsFlag = process.env.LOG_VALID_FIELDS === 'true' ? true : false; 

const loadJsonFromGCS = async (fileName) => {
	try {
		const [contents] = await storage.bucket(BUCKET_NAME).file(fileName).download();
		return JSON.parse(contents.toString());
	} catch (err) {
		if (err.code === 404) {
			console.warn(`File not found: ${fileName}`);
			return null;
		}
		throw err;
	}
};

async function logEventsToBigquery(logs) {
    let fieldsFlag;
    if (logs.length >= 1) {
        fieldsFlag = logs[ 0 ].hasOwnProperty('field');
		const dataset = bigquery.dataset(BQ_DATASET);
		const table = dataset.table(BQ_TABLE);
		table.insert(logs).catch((err) => {
			console.error('ERROR inserting logs into BigQuery:', err);
			console.dir(err, { depth: 5 });
		});
		let logged = fieldsFlag
			? `Logged ${logs.length} ${logs[0].status === 'valid' ? 'valid' : 'invalid'} fields to `
			: `Logged ${logs.length} ${logs[0].status === 'valid' ? 'valid' : 'invalid'} event to `;
		console.log(`${logged} ${BQ_DATASET}.${BQ_TABLE}`);
	} else {
        logged = fieldsFlag ? `Fields` : 'Event';
        console.log('logged', logged, ':', logs.length);
	}
	console.log('LOG_VALID_FIELDS is set to:', logValidFieldsFlag);
}

exports.loadJsonFromGCS = loadJsonFromGCS;
exports.logEventsToBigquery = logEventsToBigquery;

exports.logValidFieldsFlag = logValidFieldsFlag;
exports.BUCKET_NAME = BUCKET_NAME;
exports.BQ_DATASET = BQ_DATASET;
exports.BQ_TABLE = BQ_TABLE;
