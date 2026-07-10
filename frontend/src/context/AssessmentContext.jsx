import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { DEFAULT_ANSWERS } from '../config/schema';

// Holds the answers a student gives and the prediction we get back, so the
// results page (and its what-if panel) can read them after navigation without
// threading everything through the router.
//
// State is mirrored into sessionStorage so it survives navigating between pages
// and a page refresh. sessionStorage (not localStorage) is deliberate: it is
// cleared when the tab closes, so the promise that nothing is kept once you
// leave still holds. It is never sent anywhere except the one prediction call.
const AssessmentContext = createContext(null);

const STORAGE_KEY = 'firasa.session';

function loadPersisted() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // sessionStorage can be unavailable (private mode, blocked); fall back to memory.
  }
  return null;
}

export function AssessmentProvider({ children }) {
  const persisted = loadPersisted();
  const [answers, setAnswers] = useState(() => persisted?.answers || { ...DEFAULT_ANSWERS });
  const [result, setResult] = useState(() => persisted?.result || null);
  // Whether the student has acknowledged the consent notice this session.
  const [consented, setConsented] = useState(() => persisted?.consented || false);

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ answers, result, consented }));
    } catch {
      // Ignore write failures; the app still works from in-memory state.
    }
  }, [answers, result, consented]);

  const setAnswer = useCallback((name, value) => {
    setAnswers((prev) => ({ ...prev, [name]: value }));
  }, []);

  const acceptConsent = useCallback(() => setConsented(true), []);

  const reset = useCallback(() => {
    // Clears the answers and result but keeps consent, so a retake in the same
    // session does not prompt again.
    setAnswers({ ...DEFAULT_ANSWERS });
    setResult(null);
  }, []);

  const value = useMemo(
    () => ({ answers, setAnswer, setAnswers, result, setResult, reset, consented, acceptConsent }),
    [answers, setAnswer, result, reset, consented, acceptConsent]
  );

  return <AssessmentContext.Provider value={value}>{children}</AssessmentContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAssessment() {
  const ctx = useContext(AssessmentContext);
  if (!ctx) {
    throw new Error('useAssessment must be used inside an AssessmentProvider.');
  }
  return ctx;
}
