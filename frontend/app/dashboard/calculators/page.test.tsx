import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import CalculatorsPage from "./page";
import { calculateFullClaim, getCalculationDetail, getCalculationHistory } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  calculateFullClaim: jest.fn(),
  getCalculationHistory: jest.fn(),
  getCalculationDetail: jest.fn()
}));

const calculateFullClaimMock = calculateFullClaim as jest.MockedFunction<typeof calculateFullClaim>;
const getCalculationHistoryMock = getCalculationHistory as jest.MockedFunction<typeof getCalculationHistory>;
const getCalculationDetailMock = getCalculationDetail as jest.MockedFunction<typeof getCalculationDetail>;

describe("CalculatorsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    calculateFullClaimMock.mockResolvedValue({
      status: "ok",
      result: {
        court_fee_uah: 1500,
        penalty_uah: 3000,
        process_deadline: "2026-03-24",
        limitation_deadline: "2028-01-01",
        total_claim_uah: 103000,
        total_with_fee_uah: 104500
      },
      saved: true,
      calculation_id: "calc-1",
      created_at: "2026-02-22T12:00:00Z"
    });
    getCalculationHistoryMock.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      pages: 1,
      items: [
        {
          id: "calc-1",
          user_id: "demo-user",
          calculation_type: "full_claim",
          title: "Debt recovery calculation",
          input_payload: {},
          output_payload: {},
          notes: null,
          created_at: "2026-02-22T12:00:00Z",
          updated_at: "2026-02-22T12:00:00Z"
        }
      ]
    });
    getCalculationDetailMock.mockResolvedValue({
      item: {
        id: "calc-1",
        user_id: "demo-user",
        calculation_type: "full_claim",
        title: "Debt recovery calculation",
        input_payload: { claim_amount_uah: 100000 },
        output_payload: { total_with_fee_uah: 104500 },
        notes: null,
        created_at: "2026-02-22T12:00:00Z",
        updated_at: "2026-02-22T12:00:00Z"
      }
    });
  });

  it("calculates full claim and refreshes history", async () => {
    const user = userEvent.setup();
    render(<CalculatorsPage />);

    await user.click(screen.getByRole("button", { name: "Calculate full claim" }));
    await waitFor(() => expect(calculateFullClaimMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getCalculationHistoryMock).toHaveBeenCalledTimes(1));
    expect(screen.getByText(/Calculated and saved as calc-1/)).toBeInTheDocument();
    expect(screen.getByText(/Debt recovery calculation/)).toBeInTheDocument();
  });

  it("loads detail from history item", async () => {
    const user = userEvent.setup();
    render(<CalculatorsPage />);

    await user.click(screen.getByRole("button", { name: "Load calculation history" }));
    await waitFor(() => expect(getCalculationHistoryMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "Open" }));
    await waitFor(() => expect(getCalculationDetailMock).toHaveBeenCalledWith("calc-1", "", "demo-user"));
    expect(screen.getByText("Calculation detail")).toBeInTheDocument();
    expect(screen.getByText(/Loaded calculation calc-1/)).toBeInTheDocument();
  });
});
