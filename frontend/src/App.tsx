import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import ValidationReview from "./pages/ValidationReview";
import ClarifyingQuestions from "./pages/ClarifyingQuestions";
import NarrativePicker from "./pages/NarrativePicker";
import VerificationScreen from "./pages/VerificationScreen";
import RenderScreen from "./pages/RenderScreen";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/decks/:deckId/validate" element={<ValidationReview />} />
        <Route path="/decks/:deckId/questions" element={<ClarifyingQuestions />} />
        <Route path="/decks/:deckId/narratives" element={<NarrativePicker />} />
        <Route path="/decks/:deckId/verify" element={<VerificationScreen />} />
        <Route path="/decks/:deckId/render" element={<RenderScreen />} />
      </Routes>
    </BrowserRouter>
  );
}
