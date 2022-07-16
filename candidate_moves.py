from __future__ import annotations

from typing import List, Optional

import chess

PIECES = {'pawn': chess.PAWN, "knight": chess.KNIGHT, 'bishop': chess.BISHOP,
          'rook': chess.ROOK, 'queen': chess.QUEEN, 'king': chess.KING}
FILES = {'a': chess.BB_FILE_A, 'b': chess.BB_FILE_B, 'c': chess.BB_FILE_C,
         'd': chess.BB_FILE_D, 'e': chess.BB_FILE_E, 'f': chess.BB_FILE_F,
         'g': chess.BB_FILE_G, 'h': chess.BB_FILE_H}
RANKS = {'1': chess.BB_RANK_1, '2': chess.BB_RANK_2, '3': chess.BB_RANK_3,
         '4': chess.BB_RANK_4, '5': chess.BB_RANK_5, '6': chess.BB_RANK_6,
         '7': chess.BB_RANK_7, '8': chess.BB_RANK_8}


def is_possible_move(piece: chess.Piece, from_square: chess.Square,
                     to_square: chess.Square) -> bool:
    """
    A move is determined to be possible if the piece on from_square would be
    capable of moving to to_square if there were no other pieces on the board in
    one turn.
    """
    if piece.piece_type == PIECES['pawn']:
        # only piece that does not move same way it captures
        bb_from_square = int(chess.SquareSet.from_square(from_square))
        bb_to_square = int(chess.SquareSet.from_square(to_square))
        if piece.color == chess.WHITE:
            legal_advances = bb_from_square << 8 | \
                             (bb_from_square << 16 & RANKS['4'])
        else:
            legal_advances = bb_from_square >> 8 | \
                             (bb_from_square >> 16 & RANKS['5'])
        return bool(legal_advances & bb_to_square)
    else:
        empty = chess.BaseBoard.empty()
        # try on empty board so there are no blocking pieces
        empty.set_piece_at(from_square, piece)
        return to_square in empty.attacks(from_square)


def blocking_squares(board: chess.Board, from_square: chess.Square,
                     to_square: chess.Square) -> chess.SquareSet:
    """
    Return the set of squares with pieces that block the movement of the piece
    on from_square to to_square. This includes the piece on to_square if it is
    of the same color as the piece on from_square. The set will be empty if the
    move is not possible.

    :param board: the board state to be used for the positions of pieces
    """
    piece_squares = chess.SquareSet()
    from_piece = board.piece_at(from_square)
    to_piece = board.piece_at(to_square)
    if is_possible_move(from_piece, from_square, to_square):
        for square in chess.SquareSet.between(from_square, to_square):
            if board.piece_at(square):
                piece_squares |= square
        if to_piece and from_piece.color == to_piece.color:
            piece_squares |= to_square
    return piece_squares


def take_last(taker: SpecificSquares, board: chess.Board,
              say_promotes: Optional[str] = None) -> CommandMove:
    """
    Return a CommandMove instance of taking the opponent's last moved piece.

    :param board: the board state representing the game
    :param say_promotes: the piece to promote to,
    with no intended promotion if None
    """
    takee_square = chess.square_name(board.peek().to_square)
    takee = SpecificSquares(
        board.turn, file=takee_square[0], rank=takee_square[1])
    return CommandMove(board, taker, takee, True, say_promotes)


class SpecificSquares:
    """
    Contains info used to specify some set of squares on a chess board
    """
    color: bool
    piece: Optional[str]
    file: Optional[str]
    rank: Optional[str]

    def __init__(self, color: bool, piece: Optional[str] = None,
                 file: Optional[str] = None, rank: Optional[str] = None):
        self.color = color
        assert piece is None or piece in PIECES
        self.piece = piece
        assert file is None or file in FILES
        self.file = file
        assert rank is None or rank in RANKS
        self.rank = rank

    def __bool__(self):
        return not (self.piece == self.file == self.rank is None)

    def find_candidate_squares(self, board: chess.Board) -> chess.SquareSet:
        """
        Find the squares that match with the attributes of self. If file is the
        only attribute that is not None, the piece is assumed to be a pawn. If
        not self, any square is a candidate square.

        :param board: the board state to be used for the positions of pieces
        """
        piece_squares = chess.BB_ALL
        file_squares = chess.BB_ALL
        rank_squares = chess.BB_ALL
        if self.file:
            file_squares = FILES[self.file]
            if not self.piece and not self.rank:
                pawn_squares = board.pieces(PIECES['pawn'], self.color)
                return pawn_squares & file_squares
        if self.piece:
            piece_squares = board.pieces(PIECES[self.piece], self.color)
        if self.rank:
            rank_squares = RANKS[self.rank]
        return chess.SquareSet(piece_squares) & file_squares & rank_squares


class RejectedMove(chess.Move):
    """
    A considered move and attributes pertaining to its rejection. The move may
    not be legal on the given board state.

    === Attributes ===

    board: the board state representing the game

    possible: if the piece on the initial square is capable of moving to the
    target square if there were no other pieces on the board in one turn

    captures: if the move would result in a capture if it could legally progress
    to the target square

    blocking_pieces: the set of squares with pieces that block the movement of
    the piece on the initial square to the target square, including the target
    square itself if occupied by a friendly piece

    still_in_check: if the move cannot be made because the king would still be
    in check after its execution

    absolute_pin: if the move cannot be made because the piece to be moved
    is pinned to the king
    """
    board: chess.Board
    possible: bool
    captures: bool
    blocking_pieces: chess.SquareSet
    still_in_check: bool
    absolute_pin: bool

    def __init__(self, board: chess.Board,
                 from_square: chess.Square, to_square: chess.Square):
        super().__init__(from_square, to_square)
        self.board = board
        from_piece = board.piece_at(from_square)
        to_piece = board.piece_at(to_square)
        self.possible = is_possible_move(from_piece, from_square, to_square)
        self.blocking_pieces = blocking_squares(board, from_square, to_square)
        self.captures = bool(to_piece)
        self.still_in_check = board.is_attacked_by(not board.turn, to_square)
        self.absolute_pin = board.pin(
            from_piece.color, from_square) != chess.BB_ALL


class CastleMove(chess.Move):
    """
    A considered castle move and attributes pertaining to its rejection.
    The move may not be legal on the given board state.

    === Attributes ===

    board: the board state representing the game

    side: on which side of the board to castle

    right_to_castle: if the king and rook have not yet moved

    blocking_pieces: the set of squares between the king and rook occupied by
    pieces

    in_check: if the king is currently in check

    through_check: if the king would move through squares attacked by enemy
    pieces during castling

    into_check: if the king would be in check after castling
    """
    board: chess.Board
    side: str
    right_to_castle: bool
    blocking_pieces: chess.SquareSet
    in_check: bool
    through_check: bool
    into_check: bool

    def __init__(self, board: chess.Board, side: str):
        self.board = board
        self.side = side
        self.in_check = self.board.is_check()
        if side == 'king':
            if board.turn == chess.WHITE:
                self._castle_conditions(chess.E1, chess.F1, chess.G1)
            elif board.turn == chess.BLACK:
                self._castle_conditions(chess.E8, chess.F8, chess.G8)
        elif side == 'queen':
            if board.turn == chess.WHITE:
                self._castle_conditions(chess.E1, chess.D1, chess.C1)
            elif board.turn == chess.BLACK:
                self._castle_conditions(chess.E8, chess.D8, chess.C8)

    def _castle_conditions(self, from_square: chess.Square,
                           through_square: chess.Square,
                           to_square: chess.Square) -> None:
        if self.side == 'king':
            self.right_to_castle = \
                self.board.has_kingside_castling_rights(self.board.turn)
        elif self.side == 'queen':
            self.right_to_castle = \
                self.board.has_queenside_castling_rights(self.board.turn)
        if self.right_to_castle:
            self.blocking_pieces = \
                blocking_squares(self.board, from_square, through_square)
            if self.board.piece_at(to_square):
                self.blocking_pieces |= to_square
            # have to add to_square manually because blocking_squares would only
            # add if occupied by enemy piece
            self.through_check = \
                self.board.is_attacked_by(not self.board.turn, through_square)
            self.into_check = \
                self.board.is_attacked_by(not self.board.turn, to_square)


class BoardCommand:
    """
    A possibly ambiguous command to act on the board and the moves considered
    based on the command

    === Attributes ===

    board: the board state representing the game

    candidate_moves: the moves considered that match the full command and are
    legal

    rejected_moves: the moves considered that were rejected for at least one
    reason
    """
    board: chess.Board
    candidate_moves: List[chess.Move]
    rejected_moves: List[chess.Move]

    def __init__(self, board: chess.Board):
        self.board = board
        self.candidate_moves = []
        self.rejected_moves = []

    def consider_moves(self) -> None:
        """
        Consider all moves that are legal and match the full command. Update
        self.candidate_moves and self.rejected_moves accordingly.
        """
        raise NotImplementedError


class CommandMove(BoardCommand):
    """
    === Attributes ===

    from_where: the possible starting squares of the piece to be moved

    to_where: the possible destination squares of the piece to be moved

    captures: if the move was intended to be a capture

    promotes_to: the piece intended to be promoted to, with no intended
    promotion if None
    """
    from_where: SpecificSquares
    to_where: SpecificSquares
    captures: bool
    promotes_to: Optional[str]

    def __init__(self, board: chess.Board, from_where: SpecificSquares,
                 to_where: SpecificSquares, say_takes: bool = False,
                 say_promotes: Optional[str] = None):
        super().__init__(board)
        self.from_where = from_where
        self.to_where = to_where
        self.captures = say_takes
        self.promotes_to = say_promotes

    def consider_moves(self):
        from_squares = self.from_where.find_candidate_squares(self.board)
        to_squares = self.to_where.find_candidate_squares(self.board)
        promote_piece = PIECES.get(self.promotes_to)
        candidates = []
        rejects = []
        for from_square in from_squares:
            for to_square in to_squares:
                try:
                    candidate = self.board.find_move(
                        from_square, to_square, promote_piece)
                    # ValueError if no legal move found

                    if self.captures and not self.board.is_capture(candidate):
                        raise ValueError
                    candidates.append(candidate)
                except ValueError:
                    rejects.append(RejectedMove(
                        self.board, from_square, to_square))
        self.candidate_moves = candidates
        self.rejected_moves = rejects


class CastleCommand(BoardCommand):
    """
    === Attributes ===

    side: on which side of the board to castle
    """
    side: Optional[str]

    def __init__(self, board: chess.Board, side: Optional[str] = None):
        super().__init__(board)
        assert side in ['king', 'queen', None]
        self.side = side

    def consider_moves(self):
        candidates = []
        rejects = []
        try:  # ValueError if no legal move found
            if self.side == 'king' or not self.side:
                candidates.append(self.board.parse_san('O-O'))
        except ValueError:
            rejects.append(CastleMove(self.board, 'king'))
        try:
            if self.side == 'queen' or not self.side:
                candidates.append(self.board.parse_san('O-O-O'))
        except ValueError:
            rejects.append(CastleMove(self.board, 'queen'))
        self.candidate_moves = candidates
        self.rejected_moves = rejects
