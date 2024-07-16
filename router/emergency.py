import os

import aiohttp
from dotenv import load_dotenv
from fastapi import Request
from fastapi import APIRouter
from fastapi_utils.cbv import cbv

from interface.emergency import AmbulanceCallRequest
from interface.response import JSONResponse
load_dotenv(verbose=True)

router = APIRouter(tags=["call", "emergency"], prefix="/call")


@cbv(router)
class Emergency:
    @router.post("/emergency")
    async def emergency(self, patient_data: AmbulanceCallRequest):
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        params = {
            "y": patient_data.location_y,
            "x": patient_data.location_x,
            "radius": "20000",
            "query": "응급의료센터",
        }
        headers = {"Authorization": "KakaoAK " + os.environ["KAKAO_REST_API_KEY"]}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                result = await response.json()
        hospital = [
            item for item in result["documents"] if not "산부인과" in item["place_name"]
        ]
        return JSONResponse(
            code=200,
            message="Success",
            data={
                "name": hospital[0]["place_name"],
                "address": hospital[0]["address_name"],
                "distance": hospital[0]["distance"],
            },
            errors=[],
        )
