import speech_recognition as sr

from feedback_assistant import *
from request_assistant import decipher_request

DICTATION = sr.Recognizer()
last_spoken_command = None
last_board_command = None

# Phrases spoken by assistant
UNKNOWN = "I'm sorry, I didn't get that."


def listen_to_request(board: chess.Board) -> None:
    """
    Listen to a spoken request pertaining to the current game and perform the
    actions necessary to address it.

    :param board: the board state representing the current game
    """
    with sr.Microphone() as mic:
        DICTATION.adjust_for_ambient_noise(mic)
        print('READY')
        audio = DICTATION.listen(mic)

    try:
        global last_spoken_command
        guesser = DICTATION.recognize_sphinx(
            audio, grammar='boardRequests.gram', show_all=True)
        first_with_rejects = None
        # the first guess that leads to a BoardCommand with rejected moves
        for guess in guesser.nbest():
            # transcription guesses ordered by confidence scores
            parsed_request = decipher_request(guess.hypstr, board)
            if isinstance(parsed_request, BoardCommand):
                if not first_with_rejects and parsed_request.rejected_moves:
                    last_spoken_command = guess.hypstr
                    first_with_rejects = parsed_request
                if not parsed_request.candidate_moves:
                    # assume wrong transcription if no legal matching moves
                    continue
                last_spoken_command = guess.hypstr
            respond_to_request(parsed_request, board)
            return

        # no transcriptions with legal matching moves
        respond_to_request(first_with_rejects, board)
        # assume illegal move attempted and that command at least includes
        # square(s) with a piece to be moved

    except sr.UnknownValueError:
        assistant(UNKNOWN)
    except sr.RequestError as e:
        assistant(str(e))


def respond_to_request(parsed_request, board: chess.Board) -> None:
    if isinstance(parsed_request, BoardCommand):
        respond_to_command(parsed_request, board)
    else:
        respond_to_inquiry(parsed_request, board)


def respond_to_command(command: BoardCommand, board: chess.Board) -> None:
    global last_spoken_command, last_board_command
    last_board_command = command
    candidates = command.candidate_moves
    if candidates:
        if len(candidates) == 1:
            speak_move(candidates[0], board)
            board.push(candidates[0])
        else:
            assistant(f"The command {last_spoken_command} is ambiguous."
                      " Could you be more specific?")
    elif command.rejected_moves:
        assistant(f"The command {last_spoken_command}"
                  f" does not match any legal moves.")


def respond_to_inquiry(inquiry, board: chess.Board) -> None:
    global last_board_command
    if inquiry == 'why':  # elaborate on previous feedback
        if last_board_command.candidate_moves:
            assistant(f"Legal moves fully matching"
                      f" {last_spoken_command} include:")
            explain_why_ambiguous(last_board_command, board)
        else:
            explain_rejected_moves(last_board_command, board)
