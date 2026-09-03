//this page will store routes of all other pages
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import TravellingInputForm from "./pages/Travelling-Input-Form"
import SelectCitiesPage from "./pages/CitiesPage"
import ItineraryPage from "./pages/itinerary_Page"
import ItineraryOptions from "./pages/itinerary_Options"
import SavedItineraryPage from "./pages/SavedItineraryPage"
import "./styles/travel.css";
import "./styles/itinerary_Page.css";

function App(){
    return(
        <div className="app-shell">
            <BrowserRouter>
                <div className="page">
                    <Routes>
                        <Route path="/" element={<TravellingInputForm />}/>
                        <Route path="ItineraryPage" element={<ItineraryPage />}/>
                        <Route path="SelectCitiesPage" element={<SelectCitiesPage/>}/>
                        <Route path="ItineraryOptions" element={<ItineraryOptions/>}/>
                        <Route path="saved-itinerary/:id" element={<SavedItineraryPage/>}/>


                    </Routes>

                </div>
            </BrowserRouter>
        </div>
    )
}

export default App
