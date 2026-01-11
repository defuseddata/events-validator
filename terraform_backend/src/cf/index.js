exports.helloget = async (req, res) => {
  if (req.method !== "POST") {
    return res.status(405).send("Method Not Allowed");
  }

  // log
  console.log("Body:", req.body);

  // response
  res.status(200).send("OK");
};
