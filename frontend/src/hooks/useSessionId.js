import { useMemo } from "react";

function useSessionId(courseId) {
  return useMemo(() => {
    if (!courseId) return "";
    const key = `session-${courseId}`;
    let sid = localStorage.getItem(key);
    if (!sid) {
      sid = crypto.randomUUID();
      localStorage.setItem(key, sid);
    }
    return sid;
  }, [courseId]);
}

export default useSessionId;