def handler(request):
    return {
        "statusCode": 200,
        "body": "Hello, world! This is a test endpoint."
module.exports = (req, res) => {
  res.status(200).json({ message: "Hello, world! This is a test endpoint." });
};
