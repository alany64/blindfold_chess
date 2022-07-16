import chess
import pyttsx3

from candidate_moves import BoardCommand, CastleCommand, CommandMove, PIECES

PIECE_SYMBOLS = {'N': 'knight', 'B': 'bishop',
                 'R': 'rook', 'Q': 'queen', 'K': 'king'}

ASSISTANT = pyttsx3.init()


def assistant(text: str) -> None:
    """
    Speak the text out loud.
    """
    print(text)
    ASSISTANT.say(text)
    ASSISTANT.runAndWait()


def speak_move(move: chess.Move, board: chess.Board) -> None:
    """
    Speak the move out loud as it would be spoken if read from standard
    algebraic notation.
    """
    if board.san(move) == 'O-O':
        assistant("Kingside castles.")
        return
    elif board.san(move) == 'O-O-O':
        assistant("Queenside castles.")
        return

    move_chars = list(board.san(move))
    for i, char in enumerate(move_chars):
        if char in PIECE_SYMBOLS:
            move_chars[i] = PIECE_SYMBOLS[char]
        elif char == 'x':
            move_chars[i] = 'takes'
        elif char == '=':
            move_chars[i] = 'equals'
        elif char == '+':
            move_chars[i] = 'check'
        elif char == '#':
            move_chars[i] = 'checkmate'
    assistant(' '.join(move_chars))


def explain_why_ambiguous(command: BoardCommand, board: chess.Board) -> None:
    """
    Speak the list of legal moves that fully match command.
    """
    for move in command.candidate_moves:
        speak_move(move, board)


def _explain_broken_condition(introduction: str, moves: filter,
                              board: chess.Board) -> None:
    pieces_inverted = {v: k for k, v in PIECES.items()}
    moves = list(moves)
    if len(moves):
        assistant(introduction)
        for move in moves:
            from_square = move.from_square
            from_piece = pieces_inverted[board.piece_at(from_square).piece_type]
            assistant(f"The {from_piece} on {chess.square_name(from_square)}"
                      f" to {chess.square_name(move.to_square)}")


def explain_rejected_moves(command: BoardCommand, board: chess.Board) -> None:
    """
    Speak the reasons for why all considered moves were rejected and the moves
    associated with each reason.

    :param command: the command object containing the rejected moves
    :param board: the board state upon which the moves were considered
    """
    if isinstance(command, CommandMove):
        explain_no_moves(command, board)
    if isinstance(command, CastleCommand):
        explain_no_castle(command)


def explain_no_moves(command_move: CommandMove, board: chess.Board) -> None:
    rejects = command_move.rejected_moves
    possible_moves = list(filter(lambda move: move.possible, rejects))
    if not possible_moves:
        assistant("The piece you're trying to move cannot move like that.")
        return
    if command_move.captures:
        _explain_broken_condition(
            "The following moves are non-captures:",
            filter(lambda move: not move.captures, rejects), board)
        _explain_broken_condition(
            "The following moves are blocked by pieces:",
            filter(lambda move: move.blocking_pieces, rejects), board)
        _explain_broken_condition(
            "The following moves leave your king in check:",
            filter(lambda move: move.still_in_check, rejects), board)
        _explain_broken_condition(
            "The following moves cannot be made because the piece is "
            "pinned to the king:",
            filter(lambda move: move.absolute_pin, rejects), board)


def explain_no_castle(castle_command: CastleCommand) -> None:
    rejects = castle_command.rejected_moves
    if len(list(filter(lambda move: not move.right_to_castle, rejects))):
        assistant("You have already moved your king or rook.")
        return
    if len(list(filter(lambda move: move.blocking_pieces, rejects))):
        assistant("The path between your king and rook is not clear of pieces.")
    if len(list(filter(lambda move: move.in_check, rejects))):
        assistant("Your king is still in check.")
    if len(list(filter(lambda move: move.through_check, rejects))):
        assistant("You're attempting to castle through check.")
    if len(list(filter(lambda move: move.into_check, rejects))):
        assistant("You're attempting to castle into check.")
