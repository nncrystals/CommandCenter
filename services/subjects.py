from rx import subject

class Subjects(object):
    """
    Internal message channel multiplexier
    """
    image_producer = subject.Subject()
    image_source_connected = subject.BehaviorSubject(False)

    sample_image_data = subject.Subject()
    sample_image_producer = subject.Subject()
    detection_result = subject.Subject()

    images_to_save = subject.Subject()

    parsed_result = subject.Subject()



    def __init__(self):
        super(Subjects, self).__init__()

