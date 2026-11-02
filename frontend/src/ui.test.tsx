import { render, screen } from "@testing-library/react";
import { Empty } from "./ui";
import { fmtTime } from "./api";

test("Empty state shows title and hint", () => {
  render(<Empty title="Nothing here" hint="Start something" />);
  expect(screen.getByText("Nothing here")).toBeInTheDocument();
  expect(screen.getByText("Start something")).toBeInTheDocument();
});

test("fmtTime handles missing values", () => {
  expect(fmtTime(undefined)).toBe("");
});
