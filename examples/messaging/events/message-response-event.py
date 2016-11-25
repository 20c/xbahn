def handle_response(**kwargs):
    original_message = kwargs.get("event_origin")
    response_message = kwargs.get("message")
    print("Message received response:", response_message.data)

message = xbahn.message.Message("Test message!")
message.on("repsonse", handle_response)

link.main.send_and_wait("test", message)
