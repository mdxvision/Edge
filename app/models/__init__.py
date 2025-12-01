from app.models.nfl import NFLModel
from app.models.nba import NBAModel
from app.models.mlb import MLBModel
from app.models.nhl import NHLModel
from app.models.ncaa_football import NCAAFootballModel
from app.models.ncaa_basketball import NCAABasketballModel
from app.models.soccer import SoccerModel
from app.models.cricket import CricketModel
from app.models.rugby import RugbyModel
from app.models.tennis import TennisModel
from app.models.golf import GolfModel
from app.models.mma import MMAModel
from app.models.boxing import BoxingModel
from app.models.motorsports import MotorsportsModel
from app.models.esports import EsportsModel

SPORT_MODEL_REGISTRY = {
    "NFL": NFLModel(),
    "NBA": NBAModel(),
    "MLB": MLBModel(),
    "NHL": NHLModel(),
    "NCAA_FOOTBALL": NCAAFootballModel(),
    "NCAA_BASKETBALL": NCAABasketballModel(),
    "SOCCER": SoccerModel(),
    "CRICKET": CricketModel(),
    "RUGBY": RugbyModel(),
    "TENNIS": TennisModel(),
    "GOLF": GolfModel(),
    "MMA": MMAModel(),
    "BOXING": BoxingModel(),
    "MOTORSPORTS": MotorsportsModel(),
    "ESPORTS": EsportsModel(),
}

for model in SPORT_MODEL_REGISTRY.values():
    model.fit(None)
