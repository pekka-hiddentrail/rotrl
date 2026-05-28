import '@testing-library/jest-dom'

// jsdom does not implement scrollIntoView — stub it so ChatWindow's autoscroll
// effect does not throw in any test that renders the chat area.
window.HTMLElement.prototype.scrollIntoView = function () {}
